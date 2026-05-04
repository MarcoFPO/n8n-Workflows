from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..database import get_db
from ..services.portfolio_calculator import (
    get_current_holdings,
    get_portfolio_history,
    get_position_history,
    get_summary,
)
from ..services.tax_calculator import berechne_steuer_aus_db, zusammenfassung_nach_jahr
from ..services.price_fetcher import (
    update_all_prices, fetch_historical_prices, import_prices_from_snapshots,
    import_prices_from_acquisition_lots, fetch_all_historical_prices,
)
from datetime import date, timedelta

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/summary")
def portfolio_summary():
    conn = get_db()
    try:
        return get_summary(conn)
    finally:
        conn.close()


@router.get("/holdings")
def portfolio_holdings():
    conn = get_db()
    try:
        return get_current_holdings(conn)
    finally:
        conn.close()


@router.get("/history")
def portfolio_history():
    conn = get_db()
    try:
        return get_portfolio_history(conn)
    finally:
        conn.close()


@router.get("/history/calculated")
def portfolio_history_calculated():
    """
    Berechnet Portfoliowert und Investiert über Zeit aus Lots + Kursen.
    Liefert täglich interpolierte Werte für alle WKNs kombiniert.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()

        # Alle WKNs mit Lot-Daten
        cursor.execute("SELECT DISTINCT wkn FROM acquisition_lots")
        wkns = [r["wkn"] for r in cursor.fetchall()]

        # Alle Preisdaten je WKN laden
        cursor.execute("SELECT wkn, datum, kurs FROM prices ORDER BY wkn, datum ASC")
        prices_by_wkn: dict[str, dict[str, float]] = {}
        for r in cursor.fetchall():
            prices_by_wkn.setdefault(r["wkn"], {})[r["datum"]] = r["kurs"]

        # Tägliche Zeitachse: erster Lot bis heute (Forward-Fill)
        cursor.execute("SELECT MIN(datum) FROM acquisition_lots")
        row = cursor.fetchone()
        if not row or not row[0]:
            return []
        start_date = date.fromisoformat(row[0])
        end_date = date.today()
        all_dates = [
            (start_date + timedelta(days=i)).isoformat()
            for i in range((end_date - start_date).days + 1)
        ]

        # Je WKN: Käufe und Verkäufe laden
        position_events: dict[str, list[dict]] = {}
        for wkn in wkns:
            events = []
            cursor.execute("""
                SELECT datum, anzahl AS stueck, anschaffungskosten AS kosten, 'kauf' AS typ
                FROM acquisition_lots WHERE wkn = ? ORDER BY datum ASC
            """, (wkn,))
            for r in cursor.fetchall():
                events.append({"datum": r["datum"], "stueck": r["stueck"], "kosten": r["kosten"], "typ": "kauf"})

            cursor.execute("""
                SELECT buchungstag AS datum, ABS(stueck) AS stueck, 'verkauf' AS typ
                FROM transactions
                WHERE wkn = ? AND transaction_type IN ('verkauf', 'uebertrag_aus')
                ORDER BY buchungstag ASC
            """, (wkn,))
            for r in cursor.fetchall():
                events.append({"datum": r["datum"], "stueck": float(r["stueck"]), "kosten": 0.0, "typ": "verkauf"})

            events.sort(key=lambda e: e["datum"])
            position_events[wkn] = events

        # Für jedes globale Datum: Gesamtbestandswert + Investiert berechnen
        # running state je WKN
        states: dict[str, dict] = {wkn: {"bestand": 0.0, "investiert": 0.0, "eIdx": 0} for wkn in wkns}
        last_kurs: dict[str, float] = {}

        result = []
        for datum in all_dates:
            total_wert = 0.0
            total_investiert = 0.0
            hat_daten = False

            for wkn in wkns:
                st = states[wkn]
                events = position_events.get(wkn, [])

                # Alle Events bis einschließlich diesem Datum anwenden
                while st["eIdx"] < len(events) and events[st["eIdx"]]["datum"] <= datum:
                    ev = events[st["eIdx"]]
                    if ev["typ"] == "kauf":
                        st["bestand"] += ev["stueck"]
                        st["investiert"] += ev["kosten"]
                    else:
                        if st["bestand"] > 1e-9:
                            ratio = min(ev["stueck"] / st["bestand"], 1.0)
                            st["investiert"] -= st["investiert"] * ratio
                            st["bestand"] -= ev["stueck"]
                            st["bestand"] = max(0.0, st["bestand"])
                            st["investiert"] = max(0.0, st["investiert"])
                    st["eIdx"] += 1

                # Letzten bekannten Kurs bis zu diesem Datum merken
                wkn_prices = prices_by_wkn.get(wkn, {})
                if datum in wkn_prices:
                    last_kurs[wkn] = wkn_prices[datum]

                kurs = last_kurs.get(wkn)
                if kurs and st["bestand"] > 1e-9:
                    total_wert += st["bestand"] * kurs
                    total_investiert += st["investiert"]
                    hat_daten = True

            if hat_daten:
                result.append({
                    "datum": datum,
                    "bestandswert": round(total_wert, 2),
                    "investiert": round(total_investiert, 2),
                    "gewinn": round(total_wert - total_investiert, 2),
                })

        return result
    finally:
        conn.close()


@router.get("/tax")
def tax_overview():
    conn = get_db()
    try:
        events = berechne_steuer_aus_db(conn)
        jahres_summen = zusammenfassung_nach_jahr(events)

        return {
            "events": [
                {
                    "datum": e.datum.isoformat(),
                    "wkn": e.wkn,
                    "bezeichnung": e.bezeichnung,
                    "stueck_verkauft": round(e.stueck_verkauft, 6),
                    "erloes_eur": round(e.erloes_eur, 2),
                    "einstand_eur": round(e.einstand_eur, 2),
                    "gewinn_brutto": round(e.gewinn_brutto, 2),
                    "teilfreistellung": e.teilfreistellung,
                    "gewinn_steuerpflichtig": round(e.gewinn_steuerpflichtig, 2),
                    "steuer": round(e.steuer, 2),
                }
                for e in events
            ],
            "nach_jahr": {
                str(year): {k: round(v, 2) for k, v in data.items()}
                for year, data in sorted(jahres_summen.items())
            },
        }
    finally:
        conn.close()


@router.post("/prices/update")
def update_prices():
    conn = get_db()
    try:
        result = update_all_prices(conn)
        return {"status": "ok", "details": result}
    finally:
        conn.close()


@router.post("/prices/from-snapshots")
def prices_from_snapshots():
    """Importiert historische Kurse aus bereits importierten Depotübersichten."""
    conn = get_db()
    try:
        n = import_prices_from_snapshots(conn)
        return {"status": "ok", "importiert": n}
    finally:
        conn.close()


@router.post("/prices/history/all")
def fetch_history_all():
    """
    Lädt historische Kurse für alle WKNs:
    - Stooq: echte Tagesschlusskurse für verfügbare Ticker
    - Alle: Kaufkurse aus acquisition_lots als Datenpunkte
    - Alle: Kurse aus Depotübersichten
    """
    conn = get_db()
    try:
        # 1. Lot-Kaufkurse als Basis
        lots_n = import_prices_from_acquisition_lots(conn)
        # 2. Snapshot-Kurse
        snap_n = import_prices_from_snapshots(conn)
        # 3. Stooq historische Daten (kann 10-30s dauern)
        stooq_result = fetch_all_historical_prices(conn)
        return {
            "status": "ok",
            "lot_datenpunkte": lots_n,
            "snapshot_datenpunkte": snap_n,
            "stooq": stooq_result,
        }
    finally:
        conn.close()


@router.get("/position/{wkn}/history")
def position_history_v2(wkn: str):
    """Kursverlauf einer Position — überschreibt den alten Endpoint."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        # Zeitraum der Position ermitteln
        from ..services.portfolio_calculator import _get_position_zeitraum
        zeitraum = _get_position_zeitraum(cursor, wkn)

        # Alle Kurspunkte
        cursor.execute("""
            SELECT datum, kurs, waehrung, source FROM prices
            WHERE wkn = ? ORDER BY datum ASC
        """, (wkn,))
        preise = [{"datum": r["datum"], "kurs": r["kurs"],
                   "waehrung": r["waehrung"], "source": r["source"]}
                  for r in cursor.fetchall()]

        # Käufe (aus acquisition_lots)
        cursor.execute("""
            SELECT datum, anzahl, anschaffungskosten, kaufkurs
            FROM acquisition_lots WHERE wkn = ? ORDER BY datum ASC
        """, (wkn,))
        kaeufe = [{"datum": r["datum"], "anzahl": r["anzahl"],
                   "kurs": r["kaufkurs"], "kosten": r["anschaffungskosten"]}
                  for r in cursor.fetchall()]

        # Verkäufe und Abgänge
        cursor.execute("""
            SELECT buchungstag AS datum, stueck, transaction_type
            FROM transactions
            WHERE wkn = ? AND transaction_type IN ('verkauf', 'uebertrag_aus')
            ORDER BY buchungstag ASC
        """, (wkn,))
        verkaeufe = [{"datum": r["datum"], "stueck": abs(float(r["stueck"])), "typ": r["transaction_type"]}
                     for r in cursor.fetchall()]

        return {
            "wkn": wkn,
            "zeitraum": zeitraum,
            "preise": preise,
            "kaeufe": kaeufe,
            "verkaeufe": verkaeufe,
        }
    finally:
        conn.close()


@router.post("/prices/history/{wkn}")
def fetch_price_history(wkn: str, start: str = "2021-01-01"):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT yahoo_ticker FROM securities WHERE wkn = ?", (wkn,))
        row = cursor.fetchone()
        if not row or not row["yahoo_ticker"]:
            raise HTTPException(404, f"Kein Yahoo-Ticker für WKN {wkn} hinterlegt")

        ticker = row["yahoo_ticker"]
        prices = fetch_historical_prices(ticker, date.fromisoformat(start), date.today())

        imported = 0
        for datum, kurs in prices:
            try:
                cursor.execute(
                    """INSERT INTO prices (wkn, datum, kurs, waehrung, source)
                       VALUES (?, ?, ?, 'EUR', 'yahoo')
                       ON CONFLICT(wkn, datum) DO NOTHING""",
                    (wkn, datum.isoformat(), kurs)
                )
                imported += 1
            except Exception:
                pass

        conn.commit()
        return {"status": "ok", "wkn": wkn, "importiert": imported}
    finally:
        conn.close()


@router.get("/securities")
def list_securities():
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM securities ORDER BY bezeichnung")
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


@router.put("/securities/{wkn}")
def update_security(wkn: str, data: dict):
    conn = get_db()
    try:
        cursor = conn.cursor()
        allowed = {"yahoo_ticker", "isin", "teilfreistellung", "asset_type"}
        updates = {k: v for k, v in data.items() if k in allowed}
        if not updates:
            raise HTTPException(400, "Keine gültigen Felder angegeben")

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        cursor.execute(
            f"UPDATE securities SET {set_clause} WHERE wkn = ?",
            list(updates.values()) + [wkn]
        )
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()


@router.get("/daily-invested")
def daily_invested_all():
    """Tägliche Investitionen pro Position (alle Daten)."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT datum, wkn, bezeichnung, invested_eur, daily_total_eur
            FROM daily_invested
            ORDER BY datum ASC, wkn ASC
        """)
        rows = cursor.fetchall()
        return [
            {
                "datum": r["datum"],
                "wkn": r["wkn"],
                "bezeichnung": r["bezeichnung"],
                "invested_eur": round(r["invested_eur"], 2),
                "daily_total_eur": round(r["daily_total_eur"], 2),
            }
            for r in rows
        ]
    finally:
        conn.close()


@router.get("/daily-invested/{wkn}")
def daily_invested_by_wkn(wkn: str):
    """Tägliche Investitionen für eine spezifische Position."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT datum, invested_eur
            FROM daily_invested
            WHERE wkn = ?
            ORDER BY datum ASC
        """, (wkn,))
        rows = cursor.fetchall()
        return [
            {"datum": r["datum"], "invested_eur": round(r["invested_eur"], 2)}
            for r in rows
        ]
    finally:
        conn.close()


@router.get("/daily-gains")
def daily_gains_all():
    """Tägliche Gewinne/Verluste pro Position (alle Daten)."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT datum, wkn, bezeichnung, anzahl, kurs_eur, invested_eur,
                   wert_eur, gewinn_eur, gewinn_pct,
                   daily_total_wert, daily_total_invested, daily_total_gewinn
            FROM daily_gains
            ORDER BY datum ASC, wkn ASC
        """)
        rows = cursor.fetchall()
        return [
            {
                "datum": r["datum"],
                "wkn": r["wkn"],
                "bezeichnung": r["bezeichnung"],
                "anzahl": round(r["anzahl"], 6),
                "kurs_eur": round(r["kurs_eur"], 2) if r["kurs_eur"] else None,
                "invested_eur": round(r["invested_eur"], 2),
                "wert_eur": round(r["wert_eur"], 2) if r["wert_eur"] else None,
                "gewinn_eur": round(r["gewinn_eur"], 2) if r["gewinn_eur"] else None,
                "gewinn_pct": round(r["gewinn_pct"], 2) if r["gewinn_pct"] else None,
                "daily_total_wert": round(r["daily_total_wert"], 2) if r["daily_total_wert"] else None,
                "daily_total_invested": round(r["daily_total_invested"], 2),
                "daily_total_gewinn": round(r["daily_total_gewinn"], 2) if r["daily_total_gewinn"] else None,
            }
            for r in rows
        ]
    finally:
        conn.close()


@router.get("/daily-gains/{wkn}")
def daily_gains_by_wkn(wkn: str):
    """Tägliche Gewinne/Verluste für eine spezifische Position."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT datum, anzahl, kurs_eur, invested_eur, wert_eur,
                   gewinn_eur, gewinn_pct
            FROM daily_gains
            WHERE wkn = ?
            ORDER BY datum ASC
        """, (wkn,))
        rows = cursor.fetchall()
        return [
            {
                "datum": r["datum"],
                "anzahl": round(r["anzahl"], 6),
                "kurs_eur": round(r["kurs_eur"], 2) if r["kurs_eur"] else None,
                "invested_eur": round(r["invested_eur"], 2),
                "wert_eur": round(r["wert_eur"], 2) if r["wert_eur"] else None,
                "gewinn_eur": round(r["gewinn_eur"], 2) if r["gewinn_eur"] else None,
                "gewinn_pct": round(r["gewinn_pct"], 2) if r["gewinn_pct"] else None,
            }
            for r in rows
        ]
    finally:
        conn.close()
