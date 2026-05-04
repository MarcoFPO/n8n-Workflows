"""
Migration der Altdaten in die neuen Tabellen buys / sells / events.
Idempotent — kann beliebig oft aufgerufen werden (INSERT OR IGNORE).
"""
import hashlib
from datetime import date


def run_migration(db_conn):
    """Migriert alle Daten aus acquisition_lots + transactions in buys/sells/events."""
    cursor = db_conn.cursor()

    # ========== PHASE 1: BUYS aus acquisition_lots ==========
    cursor.execute("""
        SELECT id, wkn, bezeichnung, art, anzahl, datum, anschaffungskosten, kaufkurs, import_hash
        FROM acquisition_lots
        ORDER BY datum ASC, id ASC
    """)
    lots = cursor.fetchall()

    for lot in lots:
        art_mapped = 'kauf' if lot['art'].lower() == 'kauf' else 'uebertrag_ein'
        hash_new = _make_hash('buy|al|' + lot['import_hash'])
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO buys
                (wkn, bezeichnung, datum, anzahl, kurs_eur, gesamt_eur, waehrung,
                 art, source_table, source_id, import_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'EUR', ?, 'acquisition_lots', ?, ?, CURRENT_TIMESTAMP)
            """, (
                lot['wkn'],
                lot['bezeichnung'],
                lot['datum'],
                lot['anzahl'],
                lot['kaufkurs'],
                lot['anschaffungskosten'],
                art_mapped,
                lot['id'],
                hash_new
            ))
        except Exception as e:
            print(f"  Fehler bei Lot {lot['id']}: {e}")

    # ========== PHASE 2: BUYS aus transactions (Orphans) ==========
    # Logik: nur Käufe die NICHT durch acquisition_lots abgedeckt sind
    cursor.execute("""
        SELECT wkn FROM acquisition_lots GROUP BY wkn
    """)
    wkns_mit_lots = {row['wkn'] for row in cursor.fetchall()}

    # Für WKNs mit Lots: nimm nur Transaktionen nach dem letzten Lot-Datum
    # Für WKNs ohne Lots: nimm alle Kauftransaktionen
    cursor.execute("""
        SELECT id, wkn, bezeichnung, buchungstag, stueck, ausfuehrungskurs, umsatz_eur,
               waehrung, transaction_type, import_hash
        FROM transactions
        WHERE transaction_type IN ('kauf', 'uebertrag_ein') AND stueck > 0
        ORDER BY buchungstag ASC, id ASC
    """)
    tx_buys = cursor.fetchall()

    for tx in tx_buys:
        # Prüfe ob diesen Kauf schon ein Lot abdeckt
        if tx['wkn'] in wkns_mit_lots:
            cursor.execute(
                "SELECT MAX(datum) FROM acquisition_lots WHERE wkn = ?",
                (tx['wkn'],)
            )
            max_lot_date = cursor.fetchone()[0]
            if max_lot_date and tx['buchungstag'] <= max_lot_date:
                continue  # Lot ist älter oder gleich → Skip diesen Kauf

        # Berechne Einstandskurs
        s = abs(float(tx['stueck']))
        u = float(tx['umsatz_eur'])
        k = float(tx['ausfuehrungskurs'])
        if u != 0 and s > 0:
            kurs_eur = abs(u) / s
            gesamt_eur = abs(u)
        elif k > 0:
            kurs_eur = k
            gesamt_eur = s * k
        else:
            # Übertrag ohne Preis
            kurs_eur = 0.0
            gesamt_eur = 0.0

        art_mapped = 'kauf' if tx['transaction_type'] == 'kauf' else 'uebertrag_ein'
        hash_new = _make_hash('buy|tx|' + tx['import_hash'])

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO buys
                (wkn, bezeichnung, datum, anzahl, kurs_eur, gesamt_eur, waehrung,
                 art, source_table, source_id, import_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'transactions', ?, ?, CURRENT_TIMESTAMP)
            """, (
                tx['wkn'],
                tx['bezeichnung'],
                tx['buchungstag'],
                s,
                kurs_eur,
                gesamt_eur,
                tx['waehrung'],
                art_mapped,
                tx['id'],
                hash_new
            ))
        except Exception as e:
            print(f"  Fehler bei Kauftx {tx['id']}: {e}")

    # ========== PHASE 3: SELLS aus transactions ==========
    cursor.execute("""
        SELECT id, wkn, bezeichnung, buchungstag, stueck, ausfuehrungskurs, umsatz_eur,
               waehrung, transaction_type, import_hash
        FROM transactions
        WHERE transaction_type IN ('verkauf', 'uebertrag_aus')
        ORDER BY buchungstag ASC, id ASC
    """)
    tx_sells = cursor.fetchall()

    for tx in tx_sells:
        s = abs(float(tx['stueck']))
        u = abs(float(tx['umsatz_eur']))
        k = float(tx['ausfuehrungskurs'])

        if u > 0 and s > 0:
            kurs_eur = u / s
        else:
            kurs_eur = k if k > 0 else 0.0

        art_mapped = 'verkauf' if tx['transaction_type'] == 'verkauf' else 'uebertrag_aus'
        hash_new = _make_hash('sell|tx|' + tx['import_hash'])

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO sells
                (wkn, bezeichnung, datum, anzahl, kurs_eur, erloes_eur, waehrung,
                 art, source_id, import_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                tx['wkn'],
                tx['bezeichnung'],
                tx['buchungstag'],
                s,
                kurs_eur,
                u,
                tx['waehrung'],
                art_mapped,
                tx['id'],
                hash_new
            ))
        except Exception as e:
            print(f"  Fehler bei Verkaufstx {tx['id']}: {e}")

    # ========== PHASE 4: EVENTS aus transactions ==========
    cursor.execute("""
        SELECT id, wkn, bezeichnung, buchungstag, stueck, umsatz_eur, waehrung,
               transaction_type, import_hash
        FROM transactions
        WHERE transaction_type IN ('waehrungsumbuchung', 'unbekannt')
        ORDER BY buchungstag ASC, id ASC
    """)
    tx_events = cursor.fetchall()

    for tx in tx_events:
        hash_new = _make_hash('evt|tx|' + tx['import_hash'])

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO events
                (wkn, bezeichnung, datum, event_type, betrag_eur, stueck, waehrung,
                 source_id, import_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                tx['wkn'] if tx['transaction_type'] == 'waehrungsumbuchung' else None,
                tx['bezeichnung'],
                tx['buchungstag'],
                tx['transaction_type'],
                float(tx['umsatz_eur']),
                float(tx['stueck']),
                tx['waehrung'],
                tx['id'],
                hash_new
            ))
        except Exception as e:
            print(f"  Fehler bei Event-Tx {tx['id']}: {e}")

    db_conn.commit()


def _make_hash(content: str) -> str:
    """SHA256-Hash für Deduplizierung."""
    return hashlib.sha256(content.encode()).hexdigest()
