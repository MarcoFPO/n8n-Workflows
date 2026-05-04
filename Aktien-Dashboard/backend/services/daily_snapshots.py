"""
Tägliche Snapshots für Investitionen und Gewinne/Verluste.
Befüllt daily_invested und daily_gains basierend auf buys/sells und prices.
"""
from datetime import date, timedelta
from typing import Dict, Tuple


def calculate_daily_snapshots(db_conn):
    """
    Berechnet alle täglichen Snapshots neu.
    - Löscht alte Daten
    - Berechnet von erstem Kauf bis heute
    - Befüllt daily_invested und daily_gains
    """
    cursor = db_conn.cursor()

    # Zeitraum ermitteln
    cursor.execute("SELECT MIN(datum) FROM buys")
    start_row = cursor.fetchone()
    if not start_row or not start_row[0]:
        print("Keine Käufe vorhanden, breche ab")
        return

    start_date = date.fromisoformat(start_row[0])
    end_date = date.today()

    # Alle WKNs laden
    cursor.execute("SELECT DISTINCT wkn FROM buys")
    wkns = [row[0] for row in cursor.fetchall()]

    # Alle Kurse laden (indexed by wkn -> datum -> kurs)
    cursor.execute("SELECT wkn, datum, kurs FROM prices ORDER BY wkn, datum ASC")
    prices: Dict[str, Dict[str, float]] = {}
    for wkn, datum, kurs in cursor.fetchall():
        if wkn not in prices:
            prices[wkn] = {}
        prices[wkn][datum] = kurs

    # Alle Käufe und Verkäufe laden
    cursor.execute("SELECT wkn, datum, anzahl, gesamt_eur FROM buys ORDER BY wkn, datum ASC")
    buys = {}
    for wkn, datum, anzahl, gesamt_eur in cursor.fetchall():
        if wkn not in buys:
            buys[wkn] = []
        buys[wkn].append((datum, anzahl, gesamt_eur))

    cursor.execute("SELECT wkn, datum, anzahl FROM sells ORDER BY wkn, datum ASC")
    sells = {}
    for wkn, datum, anzahl in cursor.fetchall():
        if wkn not in sells:
            sells[wkn] = []
        sells[wkn].append((datum, anzahl))

    # Löschen alter Daten
    cursor.execute("DELETE FROM daily_invested")
    cursor.execute("DELETE FROM daily_gains")

    # State: für jeden Wkn tracken, welche Transaktionen bereits angewendet wurden
    wkn_buy_idx: Dict[str, int] = {wkn: 0 for wkn in wkns}
    wkn_sell_idx: Dict[str, int] = {wkn: 0 for wkn in wkns}

    # Tägliche Iteration
    current = start_date
    while current <= end_date:
        datum_str = current.isoformat()

        # State für diesen Tag: für jeden Wkn Bestand und investiert
        wkn_state: Dict[str, Dict] = {}

        # Alle Transaktionen bis heute anwenden
        for wkn in wkns:
            bestand = 0.0
            invested = 0.0

            # Käufe bis heute
            if wkn in buys:
                for i, (buy_datum, buy_anzahl, buy_cost) in enumerate(buys[wkn]):
                    if buy_datum <= datum_str:
                        bestand += buy_anzahl
                        invested += buy_cost

            # Verkäufe bis heute
            if wkn in sells:
                for i, (sell_datum, sell_anzahl) in enumerate(sells[wkn]):
                    if sell_datum <= datum_str:
                        bestand -= sell_anzahl

            bestand = max(0.0, bestand)
            wkn_state[wkn] = {"bestand": bestand, "invested": invested}

        # Kurse für diesen Tag laden (Forward-Fill: letzter bekannter Kurs)
        wkn_prices_today = {}
        for wkn in wkns:
            wkn_prices = prices.get(wkn, {})
            # Forward-Fill: letzter Kurs bis zu diesem Datum
            last_kurs = None
            for d_str in sorted(wkn_prices.keys()):
                if d_str <= datum_str:
                    last_kurs = wkn_prices[d_str]
                else:
                    break
            if last_kurs:
                wkn_prices_today[wkn] = last_kurs

        # daily_invested befüllen
        total_invested_today = 0.0
        for wkn in wkns:
            st = wkn_state[wkn]
            if st["invested"] > 0:
                cursor.execute("SELECT bezeichnung FROM securities WHERE wkn = ?", (wkn,))
                bez_row = cursor.fetchone()
                bez = bez_row[0] if bez_row else "Unbekannt"

                try:
                    cursor.execute("""
                        INSERT INTO daily_invested (datum, wkn, bezeichnung, invested_eur, daily_total_eur)
                        VALUES (?, ?, ?, ?, ?)
                    """, (datum_str, wkn, bez, round(st["invested"], 2), 0))
                except Exception:
                    pass

                total_invested_today += st["invested"]

        # daily_total_eur aktualisieren
        cursor.execute("UPDATE daily_invested SET daily_total_eur = ? WHERE datum = ?",
                      (round(total_invested_today, 2), datum_str))

        # daily_gains befüllen
        total_wert_today = 0.0
        total_invested_today_for_gains = 0.0
        total_gewinn_today = 0.0

        for wkn in wkns:
            st = wkn_state[wkn]
            if st["invested"] > 0 and st["bestand"] > 1e-9:
                cursor.execute("SELECT bezeichnung FROM securities WHERE wkn = ?", (wkn,))
                bez_row = cursor.fetchone()
                bez = bez_row[0] if bez_row else "Unbekannt"

                kurs = wkn_prices_today.get(wkn)
                wert = st["bestand"] * kurs if kurs else None
                gewinn = (wert - st["invested"]) if wert else None
                gewinn_pct = (gewinn / st["invested"] * 100) if st["invested"] > 0 and gewinn is not None else None

                total_invested_today_for_gains += st["invested"]
                if wert:
                    total_wert_today += wert
                    if gewinn:
                        total_gewinn_today += gewinn

                try:
                    cursor.execute("""
                        INSERT INTO daily_gains
                        (datum, wkn, bezeichnung, anzahl, kurs_eur, invested_eur, wert_eur,
                         gewinn_eur, gewinn_pct, daily_total_wert, daily_total_invested, daily_total_gewinn)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        datum_str, wkn, bez,
                        round(st["bestand"], 6),
                        round(kurs, 2) if kurs else None,
                        round(st["invested"], 2),
                        round(wert, 2) if wert else None,
                        round(gewinn, 2) if gewinn else None,
                        round(gewinn_pct, 2) if gewinn_pct else None,
                        0, 0, 0
                    ))
                except Exception:
                    pass

        # daily_totals aktualisieren
        if total_invested_today_for_gains > 0:
            cursor.execute("""
                UPDATE daily_gains
                SET daily_total_wert = ?, daily_total_invested = ?, daily_total_gewinn = ?
                WHERE datum = ?
            """, (
                round(total_wert_today, 2) if total_wert_today else None,
                round(total_invested_today_for_gains, 2),
                round(total_gewinn_today, 2) if total_gewinn_today else None,
                datum_str
            ))

        current += timedelta(days=1)

    db_conn.commit()
    print(f"Snapshots berechnet: {start_date} bis {end_date}")
