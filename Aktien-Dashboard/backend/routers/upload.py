from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import hashlib

from ..database import get_db
from ..services.csv_parser import (
    detect_file_type,
    parse_umsaetze,
    parse_depotuebersicht,
    parse_anschaffungskosten,
)
from ..services.price_fetcher import seed_known_tickers

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("")
async def upload_csv(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename or ""

    try:
        file_type = detect_file_type(filename, content)
    except ValueError as e:
        raise HTTPException(400, str(e))

    conn = get_db()
    try:
        if file_type == "umsaetze":
            return _import_umsaetze(conn, content, filename)
        elif file_type == "anschaffungskosten":
            return _import_anschaffungskosten(conn, content, filename)
        else:
            return _import_depotuebersicht(conn, content, filename)
    finally:
        conn.close()


def _import_umsaetze(conn, content: bytes, filename: str) -> JSONResponse:
    try:
        transactions = parse_umsaetze(content)
    except ValueError as e:
        raise HTTPException(400, f"Parse-Fehler: {e}")

    cursor = conn.cursor()
    imported = 0
    skipped = 0
    securities_created = 0

    for tx in transactions:
        # Security anlegen falls neu
        cursor.execute("SELECT wkn FROM securities WHERE wkn = ?", (tx.wkn,))
        if not cursor.fetchone():
            teilfreistellung = _guess_teilfreistellung(tx.bezeichnung)
            cursor.execute(
                "INSERT INTO securities (wkn, bezeichnung, teilfreistellung, asset_type) VALUES (?, ?, ?, ?)",
                (tx.wkn, tx.bezeichnung, teilfreistellung, "etf")
            )
            securities_created += 1

        # Transaktion einfügen (Duplikat via UNIQUE import_hash ignorieren)
        try:
            cursor.execute("""
                INSERT INTO transactions
                    (buchungstag, geschaeftstag, wkn, bezeichnung, stueck, waehrung,
                     ausfuehrungskurs, umsatz_eur, transaction_type, import_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tx.buchungstag.isoformat(),
                tx.geschaeftstag.isoformat(),
                tx.wkn,
                tx.bezeichnung,
                tx.stueck,
                tx.waehrung,
                tx.ausfuehrungskurs,
                tx.umsatz_eur,
                tx.transaction_type,
                tx.import_hash,
            ))
            tx_id = cursor.lastrowid

            # Dual-Write: auch in buys/sells/events schreiben
            _insert_transaction_to_new_tables(cursor, tx, tx_id, tx.import_hash)

            imported += 1
        except Exception:
            skipped += 1

    seed_known_tickers(conn)
    conn.commit()

    return JSONResponse({
        "status": "ok",
        "datei": filename,
        "typ": "umsaetze",
        "importiert": imported,
        "duplikate_ignoriert": skipped,
        "neue_wertpapiere": securities_created,
    })


def _import_depotuebersicht(conn, content: bytes, filename: str) -> JSONResponse:
    try:
        snapshot_date, snapshots = parse_depotuebersicht(content)
    except ValueError as e:
        raise HTTPException(400, f"Parse-Fehler: {e}")

    cursor = conn.cursor()
    imported = 0

    for snap in snapshots:
        cursor.execute("""
            INSERT INTO depot_snapshots
                (snapshot_date, bezeichnung, stueck, aktueller_kurs, wert_eur,
                 diff_seit_kauf_abs, diff_seit_kauf_rel, schlusskurs, schlusskurs_waehrung)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snap.snapshot_date.isoformat(),
            snap.bezeichnung,
            snap.stueck,
            snap.aktueller_kurs,
            snap.wert_eur,
            snap.diff_seit_kauf_abs,
            snap.diff_seit_kauf_rel,
            snap.schlusskurs,
            snap.schlusskurs_waehrung,
        ))
        imported += 1

    conn.commit()

    return JSONResponse({
        "status": "ok",
        "datei": filename,
        "typ": "depotuebersicht",
        "datum": snapshot_date.isoformat(),
        "importiert": imported,
    })


def _import_anschaffungskosten(conn, content: bytes, filename: str) -> JSONResponse:
    try:
        lots = parse_anschaffungskosten(content)
    except ValueError as e:
        raise HTTPException(400, f"Parse-Fehler: {e}")

    cursor = conn.cursor()
    imported = 0
    skipped = 0
    securities_created = 0

    for lot in lots:
        # Security anlegen falls neu
        cursor.execute("SELECT wkn FROM securities WHERE wkn = ?", (lot.wkn,))
        if not cursor.fetchone():
            teilfreistellung = _guess_teilfreistellung(lot.bezeichnung)
            cursor.execute(
                "INSERT INTO securities (wkn, bezeichnung, teilfreistellung, asset_type) VALUES (?, ?, ?, ?)",
                (lot.wkn, lot.bezeichnung, teilfreistellung, "etf")
            )
            securities_created += 1

        try:
            cursor.execute("""
                INSERT INTO acquisition_lots
                    (wkn, bezeichnung, art, anzahl, datum, anschaffungskosten, kaufkurs, import_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lot.wkn,
                lot.bezeichnung,
                lot.art,
                lot.anzahl,
                lot.datum.isoformat(),
                lot.anschaffungskosten,
                lot.kaufkurs,
                lot.import_hash,
            ))
            lot_id = cursor.lastrowid

            # Dual-Write: auch in buys schreiben
            _insert_lot_to_buys(cursor, lot, lot_id, lot.import_hash)

            imported += 1
        except Exception:
            skipped += 1

    seed_known_tickers(conn)
    conn.commit()

    return JSONResponse({
        "status": "ok",
        "datei": filename,
        "typ": "anschaffungskosten",
        "importiert": imported,
        "duplikate_ignoriert": skipped,
        "neue_wertpapiere": securities_created,
    })


def _guess_teilfreistellung(bezeichnung: str) -> float:
    """Schätzt Teilfreistellung anhand des Namens (Standard 30% für ETFs/Fonds)."""
    bez = bezeichnung.upper()
    # Misch-ETFs haben 15%
    if any(k in bez for k in ("MISCH", "BALANCED", "MULTI-ASSET")):
        return 0.15
    # Renten-ETFs: 0%
    if any(k in bez for k in ("BOND", "RENTEN", "ANLEIHE", "GOVT", "TREASURY")):
        return 0.0
    # Alles andere (Aktien-ETF, Fonds): 30%
    return 0.30


def _make_hash(content: str) -> str:
    """SHA256-Hash für Deduplizierung."""
    return hashlib.sha256(content.encode()).hexdigest()


def _insert_transaction_to_new_tables(cursor, tx, tx_id: int, import_hash: str):
    """Schreibt eine Transaction in die entsprechende neue Tabelle (buys/sells/events)."""
    if tx.transaction_type in ('kauf', 'uebertrag_ein') and tx.stueck > 0:
        _insert_buy_from_transaction(cursor, tx, tx_id, import_hash)
    elif tx.transaction_type in ('verkauf', 'uebertrag_aus'):
        _insert_sell_from_transaction(cursor, tx, tx_id, import_hash)
    elif tx.transaction_type in ('waehrungsumbuchung', 'unbekannt'):
        _insert_event_from_transaction(cursor, tx, tx_id, import_hash)


def _insert_buy_from_transaction(cursor, tx, tx_id: int, import_hash: str):
    """Schreibt einen Kauf aus Transaction in buys."""
    s = abs(float(tx.stueck))
    u = float(tx.umsatz_eur)
    k = float(tx.ausfuehrungskurs)

    if u != 0 and s > 0:
        kurs_eur = abs(u) / s
        gesamt_eur = abs(u)
    elif k > 0:
        kurs_eur = k
        gesamt_eur = s * k
    else:
        kurs_eur = 0.0
        gesamt_eur = 0.0

    art_mapped = 'kauf' if tx.transaction_type == 'kauf' else 'uebertrag_ein'
    hash_new = _make_hash('buy|tx|' + import_hash)

    try:
        cursor.execute("""
            INSERT OR IGNORE INTO buys
            (wkn, bezeichnung, datum, anzahl, kurs_eur, gesamt_eur, waehrung,
             art, source_table, source_id, import_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'transactions', ?, ?)
        """, (
            tx.wkn,
            tx.bezeichnung,
            tx.geschaeftstag.isoformat(),
            s,
            kurs_eur,
            gesamt_eur,
            tx.waehrung,
            art_mapped,
            tx_id,
            hash_new
        ))
    except Exception:
        pass  # Duplikat oder Fehler — ignorieren


def _insert_sell_from_transaction(cursor, tx, tx_id: int, import_hash: str):
    """Schreibt einen Verkauf aus Transaction in sells."""
    s = abs(float(tx.stueck))
    u = abs(float(tx.umsatz_eur))
    k = float(tx.ausfuehrungskurs)

    if u > 0 and s > 0:
        kurs_eur = u / s
    else:
        kurs_eur = k if k > 0 else 0.0

    art_mapped = 'verkauf' if tx.transaction_type == 'verkauf' else 'uebertrag_aus'
    hash_new = _make_hash('sell|tx|' + import_hash)

    try:
        cursor.execute("""
            INSERT OR IGNORE INTO sells
            (wkn, bezeichnung, datum, anzahl, kurs_eur, erloes_eur, waehrung,
             art, source_id, import_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tx.wkn,
            tx.bezeichnung,
            tx.geschaeftstag.isoformat(),
            s,
            kurs_eur,
            u,
            tx.waehrung,
            art_mapped,
            tx_id,
            hash_new
        ))
    except Exception:
        pass  # Duplikat oder Fehler — ignorieren


def _insert_event_from_transaction(cursor, tx, tx_id: int, import_hash: str):
    """Schreibt ein Event (Währungsumbuchung, etc.) aus Transaction in events."""
    hash_new = _make_hash('evt|tx|' + import_hash)

    try:
        cursor.execute("""
            INSERT OR IGNORE INTO events
            (wkn, bezeichnung, datum, event_type, betrag_eur, stueck, waehrung,
             source_id, import_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tx.wkn if tx.transaction_type == 'waehrungsumbuchung' else None,
            tx.bezeichnung,
            tx.geschaeftstag.isoformat(),
            tx.transaction_type,
            float(tx.umsatz_eur),
            float(tx.stueck),
            tx.waehrung,
            tx_id,
            hash_new
        ))
    except Exception:
        pass  # Duplikat oder Fehler — ignorieren


def _insert_lot_to_buys(cursor, lot, lot_id: int, import_hash: str):
    """Schreibt einen Lot aus acquisition_lots in buys."""
    art_mapped = 'kauf' if lot.art.lower() == 'kauf' else 'uebertrag_ein'
    hash_new = _make_hash('buy|al|' + import_hash)

    try:
        cursor.execute("""
            INSERT OR IGNORE INTO buys
            (wkn, bezeichnung, datum, anzahl, kurs_eur, gesamt_eur, waehrung,
             art, source_table, source_id, import_hash)
            VALUES (?, ?, ?, ?, ?, ?, 'EUR', ?, 'acquisition_lots', ?, ?)
        """, (
            lot.wkn,
            lot.bezeichnung,
            lot.datum.isoformat(),
            lot.anzahl,
            lot.kaufkurs,
            lot.anschaffungskosten,
            art_mapped,
            lot_id,
            hash_new
        ))
    except Exception:
        pass  # Duplikat oder Fehler — ignorieren
