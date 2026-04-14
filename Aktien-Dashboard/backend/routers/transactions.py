from fastapi import APIRouter, Query
from ..database import get_db

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("")
def list_transactions(
    wkn: str | None = Query(None),
    tx_type: str | None = Query(None),
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
):
    """
    Listet Transaktionen aus den neuen Tabellen (buys/sells/events).
    Kombiniert alle Transaktionsquellen mit UNION für einheitliche API.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()

        # Bedingungen bauen
        wkn_filter = f"AND wkn = '{wkn}'" if wkn else ""

        # Type-basierte Filter für UNION-Teile
        buy_condition = ""
        sell_condition = ""
        event_condition = ""

        if tx_type:
            if tx_type == "Zugang":
                # Alle Zugang-Arten einschließen (kauf, uebertrag_ein, imports)
                pass  # buy_condition bleibt leer, alle buys werden gefiltert
            elif tx_type == "Abgang":
                # Alle Abgang-Arten einschließen (verkauf, uebertrag_aus, imports)
                pass  # sell_condition bleibt leer, alle sells werden gefiltert
            elif tx_type == "waehrungsumbuchung":
                event_condition = "AND event_type = 'waehrungsumbuchung'"
            # Backward-Compatibility für alte Filter (für UI-Links)
            elif tx_type == "kauf":
                buy_condition = "AND art = 'kauf'"
            elif tx_type == "uebertrag_ein":
                buy_condition = "AND art = 'uebertrag_ein'"
            elif tx_type == "verkauf":
                sell_condition = "AND art = 'verkauf'"
            elif tx_type == "uebertrag_aus":
                sell_condition = "AND art = 'uebertrag_aus'"

        # Unified transactions query: alle Quellen kombiniert
        query_parts = []
        params = []

        # Buys (wenn kein type_filter oder "Zugang" oder alte Kategorien wie "kauf")
        if not tx_type or tx_type in ("Zugang", "kauf", "uebertrag_ein"):
            query_parts.append(f"""
                SELECT
                    datum as buchungstag,
                    wkn,
                    bezeichnung,
                    anzahl as stueck,
                    kurs_eur as ausfuehrungskurs,
                    waehrung,
                    gesamt_eur as umsatz_eur,
                    typ as transaction_type,
                    art as transaction_subtype
                FROM buys
                WHERE 1=1 {wkn_filter} {buy_condition}
            """)

        # Sells (wenn kein type_filter oder "Abgang" oder alte Kategorien)
        if not tx_type or tx_type in ("Abgang", "verkauf", "uebertrag_aus"):
            query_parts.append(f"""
                SELECT
                    datum as buchungstag,
                    wkn,
                    bezeichnung,
                    anzahl as stueck,
                    kurs_eur as ausfuehrungskurs,
                    waehrung,
                    erloes_eur as umsatz_eur,
                    typ as transaction_type,
                    art as transaction_subtype
                FROM sells
                WHERE 1=1 {wkn_filter} {sell_condition}
            """)

        # Events (wenn kein type_filter oder nur Währungsumbucht)
        if not tx_type or tx_type == "waehrungsumbuchung":
            query_parts.append(f"""
                SELECT
                    datum as buchungstag,
                    wkn,
                    bezeichnung,
                    stueck,
                    0.0 as ausfuehrungskurs,
                    waehrung,
                    betrag_eur as umsatz_eur,
                    event_type as transaction_type
                FROM events
                WHERE 1=1 {wkn_filter} {event_condition}
            """)

        # Kombinieren und ausführen
        if query_parts:
            full_query = " UNION ALL ".join(query_parts) + " ORDER BY datum DESC LIMIT ? OFFSET ?"
            cursor.execute(full_query, [limit, offset])
            rows = [dict(r) for r in cursor.fetchall()]
        else:
            rows = []

        # Count für Pagination
        count_parts = []

        if not tx_type or tx_type in ("Zugang", "kauf", "uebertrag_ein"):
            count_parts.append(f"SELECT 1 FROM buys WHERE 1=1 {wkn_filter} {buy_condition}")

        if not tx_type or tx_type in ("Abgang", "verkauf", "uebertrag_aus"):
            count_parts.append(f"SELECT 1 FROM sells WHERE 1=1 {wkn_filter} {sell_condition}")

        if not tx_type or tx_type == "waehrungsumbuchung":
            count_parts.append(f"SELECT 1 FROM events WHERE 1=1 {wkn_filter} {event_condition}")

        if count_parts:
            count_query = f"SELECT COUNT(*) as cnt FROM ({' UNION ALL '.join(count_parts)})"
            cursor.execute(count_query)
            total = cursor.fetchone()["cnt"]
        else:
            total = 0

        return {"total": total, "items": rows}
    finally:
        conn.close()
