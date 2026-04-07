"""
Portfolio-Berechnungen: aktueller Bestand, Wertentwicklung, Kennzahlen.

FIFO-Quellen (Priorität):
1. acquisition_lots  — exakte Lots aus Anschaffungskosten-CSV (ab 2019)
2. transactions      — Käufe/Überträge aus Umsätze-CSV als Fallback für nicht erfasste Lots

Verkäufe kommen immer aus transactions.
"""
from collections import defaultdict
from datetime import date


def _build_lots_from_acquisition(cursor, wkn: str) -> list[dict]:
    """Gibt alle Lots für eine WKN aus acquisition_lots zurück (chronologisch)."""
    cursor.execute("""
        SELECT datum, anzahl, anschaffungskosten, kaufkurs
        FROM acquisition_lots
        WHERE wkn = ?
        ORDER BY datum ASC, id ASC
    """, (wkn,))
    return [
        {"stueck": row["anzahl"], "kurs_eur": row["anschaffungskosten"] / row["anzahl"] if row["anzahl"] > 0 else row["kaufkurs"]}
        for row in cursor.fetchall()
    ]


def _has_acquisition_lots(cursor, wkn: str) -> bool:
    cursor.execute("SELECT 1 FROM acquisition_lots WHERE wkn = ? LIMIT 1", (wkn,))
    return cursor.fetchone() is not None


def get_current_holdings(db_conn) -> list[dict]:
    """
    Berechnet den aktuellen Bestand via FIFO.
    Nutzt acquisition_lots als primäre Quelle, transactions als Fallback.
    """
    cursor = db_conn.cursor()

    # Alle WKNs mit Aktivität ermitteln
    cursor.execute("""
        SELECT DISTINCT wkn FROM transactions
        UNION
        SELECT DISTINCT wkn FROM acquisition_lots
    """)
    all_wkns = [row["wkn"] for row in cursor.fetchall()]

    # Securities-Metadaten
    cursor.execute("SELECT wkn, bezeichnung, teilfreistellung, yahoo_ticker FROM securities")
    sec_meta = {r["wkn"]: dict(r) for r in cursor.fetchall()}

    # Aktuellen Kurs je WKN
    cursor.execute("""
        SELECT p1.wkn, p1.kurs, p1.waehrung
        FROM prices p1
        INNER JOIN (SELECT wkn, MAX(datum) AS max_datum FROM prices GROUP BY wkn) p2
            ON p1.wkn = p2.wkn AND p1.datum = p2.max_datum
    """)
    current_prices = {row["wkn"]: {"kurs": row["kurs"], "waehrung": row["waehrung"]}
                      for row in cursor.fetchall()}

    holdings = []

    for wkn in all_wkns:
        # Verkäufe und Überträge-Aus aus transactions
        cursor.execute("""
            SELECT buchungstag, stueck, umsatz_eur, ausfuehrungskurs, transaction_type
            FROM transactions
            WHERE wkn = ? AND transaction_type IN ('verkauf', 'uebertrag_aus', 'waehrungsumbuchung')
            ORDER BY buchungstag ASC, id ASC
        """, (wkn,))
        abgaenge = [dict(r) for r in cursor.fetchall()]

        if _has_acquisition_lots(cursor, wkn):
            # Primärquelle: acquisition_lots
            lots = _build_lots_from_acquisition(cursor, wkn)

            # Zusätzliche Käufe aus transactions die NICHT in acquisition_lots stecken
            # (erkennbar: Datum nach dem letzten acquisition_lot-Datum)
            cursor.execute("SELECT MAX(datum) FROM acquisition_lots WHERE wkn = ?", (wkn,))
            max_lot_date = cursor.fetchone()[0]

            cursor.execute("""
                SELECT buchungstag, stueck, umsatz_eur, ausfuehrungskurs, transaction_type
                FROM transactions
                WHERE wkn = ? AND transaction_type IN ('kauf', 'uebertrag_ein', 'waehrungsumbuchung')
                  AND buchungstag > ?
                ORDER BY buchungstag ASC, id ASC
            """, (wkn, max_lot_date or "2000-01-01"))
            for tx in cursor.fetchall():
                s = abs(float(tx["stueck"]))
                u = float(tx["umsatz_eur"])
                k = float(tx["ausfuehrungskurs"])
                if float(tx["stueck"]) > 0:
                    kurs_eur = abs(u) / s if s > 0 and u != 0 else k
                    lots.append({"stueck": s, "kurs_eur": kurs_eur})
        else:
            # Fallback: nur transactions
            cursor.execute("""
                SELECT buchungstag, stueck, umsatz_eur, ausfuehrungskurs, transaction_type
                FROM transactions
                WHERE wkn = ? AND transaction_type IN ('kauf', 'uebertrag_ein', 'waehrungsumbuchung')
                ORDER BY buchungstag ASC, id ASC
            """, (wkn,))
            lots = []
            for tx in cursor.fetchall():
                s = abs(float(tx["stueck"]))
                u = float(tx["umsatz_eur"])
                k = float(tx["ausfuehrungskurs"])
                if float(tx["stueck"]) > 0:
                    kurs_eur = abs(u) / s if s > 0 and u != 0 else k
                    lots.append({"stueck": s, "kurs_eur": kurs_eur})

        # Abgänge via FIFO verarbeiten
        for tx in abgaenge:
            s = abs(float(tx["stueck"]))
            _consume_fifo(lots, s)

        total_stueck = sum(l["stueck"] for l in lots)
        geschlossen = total_stueck < 1e-6

        meta = sec_meta.get(wkn, {"bezeichnung": wkn, "teilfreistellung": 0.30, "yahoo_ticker": None})
        price_info = current_prices.get(wkn)
        aktueller_kurs = price_info["kurs"] if price_info else None

        if geschlossen:
            # Einstand aus allen jemals gekauften Lots rekonstruieren (für Info-Anzeige)
            einstand_eur = _total_invested(cursor, wkn)
            # Letzter Kurspunkt aus prices
            cursor.execute(
                "SELECT kurs FROM prices WHERE wkn = ? ORDER BY datum DESC LIMIT 1", (wkn,)
            )
            pk = cursor.fetchone()
            aktueller_kurs = pk["kurs"] if pk else None
            aktueller_wert = None
            gewinn = None
            rendite = None
            # Zeitraum der Position ermitteln
            zeitraum = _get_position_zeitraum(cursor, wkn)
        else:
            einstand_eur = sum(l["stueck"] * l["kurs_eur"] for l in lots)
            aktueller_wert = total_stueck * aktueller_kurs if aktueller_kurs else None
            gewinn = (aktueller_wert - einstand_eur) if aktueller_wert is not None else None
            rendite = (gewinn / einstand_eur * 100) if (gewinn is not None and einstand_eur > 0) else None
            zeitraum = None

        holdings.append({
            "wkn": wkn,
            "bezeichnung": meta["bezeichnung"],
            "stueck": round(total_stueck, 6),
            "geschlossen": geschlossen,
            "einstand_eur": round(einstand_eur, 2),
            "einstand_kurs": round(einstand_eur / total_stueck, 4) if total_stueck > 0 else 0,
            "aktueller_kurs": round(aktueller_kurs, 4) if aktueller_kurs else None,
            "aktueller_wert": round(aktueller_wert, 2) if aktueller_wert else None,
            "gewinn_unrealisiert": round(gewinn, 2) if gewinn is not None else None,
            "rendite_prozent": round(rendite, 2) if rendite is not None else None,
            "teilfreistellung": meta.get("teilfreistellung", 0.30),
            "hat_lot_daten": _has_acquisition_lots(cursor, wkn),
            "zeitraum": zeitraum,
        })

    aktiv = [h for h in holdings if not h["geschlossen"]]
    geschl = [h for h in holdings if h["geschlossen"]]
    return (
        sorted(aktiv, key=lambda h: (h["aktueller_wert"] or 0), reverse=True) +
        sorted(geschl, key=lambda h: h["bezeichnung"])
    )


def get_portfolio_history(db_conn) -> list[dict]:
    """Portfolio-Entwicklung über Zeit aus Depotübersichten.

    Investiertes Kapital wird aus Transaktionen berechnet (Netto-Investitionen),
    nicht aus Depotübersichten, um Umschichtungen korrekt zu erfassen.
    """
    cursor = db_conn.cursor()

    # Alle Snapshot-Daten laden
    cursor.execute("""
        SELECT snapshot_date,
               SUM(wert_eur) AS depotwert
        FROM depot_snapshots
        GROUP BY snapshot_date
        ORDER BY snapshot_date ASC
    """)
    snapshots = cursor.fetchall()

    result = []
    for row in snapshots:
        snapshot_date = row["snapshot_date"]
        depotwert = row["depotwert"] or 0

        # Netto-Investiertes Kapital bis zu diesem Datum aus Transaktionen
        # Käufe: investiertes Kapital (positiv)
        # Verkäufe: Rückfluss von Kapital (reduziert Netto-Investition)
        cursor.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN transaction_type = 'kauf' THEN ABS(umsatz_eur) ELSE 0 END), 0) AS kaeufe,
                COALESCE(SUM(CASE WHEN transaction_type = 'verkauf' THEN ABS(umsatz_eur) ELSE 0 END), 0) AS verkaeufe
            FROM transactions
            WHERE buchungstag <= ?
        """, (snapshot_date,))

        tx_row = cursor.fetchone()
        kaeufe = tx_row["kaeufe"] or 0
        verkaeufe = tx_row["verkaeufe"] or 0

        # Netto-Investition = investiertes Kapital - Rückflüsse aus Verkäufen
        investiert = kaeufe - verkaeufe
        gewinn = depotwert - investiert

        result.append({
            "datum": snapshot_date,
            "depotwert": round(depotwert, 2),
            "investiert": round(investiert, 2),
            "gewinn": round(gewinn, 2),
        })

    return result


def get_position_history(db_conn, wkn: str) -> list[dict]:
    """Kursverlauf einer einzelnen Position."""
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT datum, kurs, waehrung FROM prices
        WHERE wkn = ? ORDER BY datum ASC
    """, (wkn,))
    return [{"datum": r["datum"], "kurs": r["kurs"], "waehrung": r["waehrung"]}
            for r in cursor.fetchall()]


def get_summary(db_conn) -> dict:
    """Gesamtzusammenfassung des Depots."""
    holdings = get_current_holdings(db_conn)
    total_invested = sum(h["einstand_eur"] for h in holdings)
    total_value = sum(h["aktueller_wert"] or h["einstand_eur"] for h in holdings)
    total_gain = sum(h["gewinn_unrealisiert"] or 0 for h in holdings)

    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) AS cnt FROM transactions WHERE transaction_type = 'verkauf'")
    verkauf_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) AS cnt FROM acquisition_lots")
    lot_count = cursor.fetchone()["cnt"]

    return {
        "total_invested": round(total_invested, 2),
        "total_value": round(total_value, 2),
        "total_gain_unrealized": round(total_gain, 2),
        "rendite_gesamt": round(total_gain / total_invested * 100, 2) if total_invested > 0 else 0,
        "anzahl_positionen": len(holdings),
        "anzahl_verkaeufe": verkauf_count,
        "anzahl_lots": lot_count,
    }


def _consume_fifo(lots: list[dict], stueck_benoetigt: float):
    """Verbraucht Lots nach FIFO (in-place)."""
    noch = stueck_benoetigt
    while lots and noch > 1e-9:
        if lots[0]["stueck"] <= noch + 1e-9:
            noch -= lots[0]["stueck"]
            lots.pop(0)
        else:
            lots[0]["stueck"] -= noch
            noch = 0.0


def _total_invested(cursor, wkn: str) -> float:
    """Gesamt investierter Betrag für eine WKN (Summe aller Anschaffungskosten)."""
    cursor.execute(
        "SELECT COALESCE(SUM(anschaffungskosten), 0) FROM acquisition_lots WHERE wkn = ?", (wkn,)
    )
    row = cursor.fetchone()
    return float(row[0]) if row else 0.0


def _get_position_zeitraum(cursor, wkn: str) -> dict | None:
    """Ermittelt Anfangs- und Enddatum einer Position."""
    cursor.execute("""
        SELECT MIN(datum) AS von FROM acquisition_lots WHERE wkn = ?
    """, (wkn,))
    row = cursor.fetchone()
    von = row["von"] if row and row["von"] else None

    cursor.execute("""
        SELECT MAX(buchungstag) AS bis FROM transactions
        WHERE wkn = ? AND transaction_type = 'verkauf'
    """, (wkn,))
    row = cursor.fetchone()
    bis = row["bis"] if row and row["bis"] else None

    if not von:
        cursor.execute("SELECT MIN(buchungstag) FROM transactions WHERE wkn = ?", (wkn,))
        r = cursor.fetchone()
        von = r[0] if r else None

    return {"von": von, "bis": bis} if von else None
