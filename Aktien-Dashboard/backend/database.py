import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "aktien.db"


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS securities (
        wkn              TEXT PRIMARY KEY,
        bezeichnung      TEXT NOT NULL,
        isin             TEXT,
        yahoo_ticker     TEXT,
        teilfreistellung REAL NOT NULL DEFAULT 0.0,
        asset_type       TEXT NOT NULL DEFAULT 'etf',
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        buchungstag          DATE NOT NULL,
        geschaeftstag        DATE NOT NULL,
        wkn                  TEXT NOT NULL,
        bezeichnung          TEXT NOT NULL,
        stueck               REAL NOT NULL,
        waehrung             TEXT NOT NULL,
        ausfuehrungskurs     REAL NOT NULL,
        umsatz_eur           REAL NOT NULL,
        transaction_type     TEXT NOT NULL,
        import_hash          TEXT UNIQUE NOT NULL,
        created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (wkn) REFERENCES securities(wkn)
    );

    CREATE TABLE IF NOT EXISTS depot_snapshots (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_date        DATE NOT NULL,
        bezeichnung          TEXT NOT NULL,
        stueck               REAL NOT NULL,
        aktueller_kurs       REAL,
        wert_eur             REAL,
        diff_seit_kauf_abs   REAL,
        diff_seit_kauf_rel   REAL,
        schlusskurs          REAL,
        schlusskurs_waehrung TEXT,
        created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS prices (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        wkn        TEXT NOT NULL,
        datum      DATE NOT NULL,
        kurs       REAL NOT NULL,
        waehrung   TEXT NOT NULL DEFAULT 'EUR',
        source     TEXT DEFAULT 'yahoo',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(wkn, datum),
        FOREIGN KEY (wkn) REFERENCES securities(wkn)
    );

    CREATE TABLE IF NOT EXISTS acquisition_lots (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        wkn               TEXT NOT NULL,
        bezeichnung       TEXT NOT NULL,
        art               TEXT NOT NULL,
        anzahl            REAL NOT NULL,
        datum             DATE NOT NULL,
        anschaffungskosten REAL NOT NULL,
        kaufkurs          REAL NOT NULL,
        import_hash       TEXT UNIQUE NOT NULL,
        created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (wkn) REFERENCES securities(wkn)
    );

    CREATE INDEX IF NOT EXISTS idx_transactions_wkn       ON transactions(wkn);
    CREATE INDEX IF NOT EXISTS idx_transactions_datum     ON transactions(buchungstag);
    CREATE INDEX IF NOT EXISTS idx_prices_wkn_datum       ON prices(wkn, datum);
    CREATE INDEX IF NOT EXISTS idx_snapshots_date         ON depot_snapshots(snapshot_date);
    CREATE INDEX IF NOT EXISTS idx_lots_wkn_datum         ON acquisition_lots(wkn, datum);

    -- Neue, saubere Tabellen für Käufe, Verkäufe und Ereignisse
    CREATE TABLE IF NOT EXISTS buys (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        wkn           TEXT NOT NULL,
        bezeichnung   TEXT NOT NULL,
        datum         DATE NOT NULL,
        anzahl        REAL NOT NULL,
        kurs_eur      REAL NOT NULL,
        gesamt_eur    REAL NOT NULL,
        waehrung      TEXT NOT NULL DEFAULT 'EUR',
        art           TEXT NOT NULL DEFAULT 'kauf',
        source_table  TEXT NOT NULL,
        source_id     INTEGER,
        import_hash   TEXT UNIQUE NOT NULL,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (wkn) REFERENCES securities(wkn)
    );

    CREATE TABLE IF NOT EXISTS sells (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        wkn           TEXT NOT NULL,
        bezeichnung   TEXT NOT NULL,
        datum         DATE NOT NULL,
        anzahl        REAL NOT NULL,
        kurs_eur      REAL NOT NULL,
        erloes_eur    REAL NOT NULL,
        waehrung      TEXT NOT NULL DEFAULT 'EUR',
        art           TEXT NOT NULL DEFAULT 'verkauf',
        source_id     INTEGER,
        import_hash   TEXT UNIQUE NOT NULL,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (wkn) REFERENCES securities(wkn)
    );

    CREATE TABLE IF NOT EXISTS events (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        wkn           TEXT,
        bezeichnung   TEXT,
        datum         DATE NOT NULL,
        event_type    TEXT NOT NULL,
        betrag_eur    REAL,
        stueck        REAL,
        waehrung      TEXT,
        beschreibung  TEXT,
        source_id     INTEGER,
        import_hash   TEXT UNIQUE NOT NULL,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_buys_wkn_datum    ON buys(wkn, datum);
    CREATE INDEX IF NOT EXISTS idx_sells_wkn_datum   ON sells(wkn, datum);
    CREATE INDEX IF NOT EXISTS idx_events_datum      ON events(datum);
    CREATE INDEX IF NOT EXISTS idx_events_wkn        ON events(wkn);

    -- Tägliche Aggregationen: Investierte Beträge pro Position und Datum
    CREATE TABLE IF NOT EXISTS daily_invested (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        datum             DATE NOT NULL,
        wkn               TEXT NOT NULL,
        bezeichnung       TEXT NOT NULL,
        invested_eur      REAL NOT NULL,          -- Kumulierte Anschaffungskosten bis zu diesem Tag
        daily_total_eur   REAL NOT NULL,          -- Summe aller Positionen an diesem Tag
        created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(datum, wkn),
        FOREIGN KEY (wkn) REFERENCES securities(wkn)
    );

    -- Tägliche Aggregationen: Gewinne/Verluste pro Position und Datum
    CREATE TABLE IF NOT EXISTS daily_gains (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        datum                 DATE NOT NULL,
        wkn                   TEXT NOT NULL,
        bezeichnung           TEXT NOT NULL,
        anzahl                REAL NOT NULL,           -- Bestand an diesem Tag
        kurs_eur              REAL,                    -- Kurs an diesem Tag (NULL wenn nicht verfügbar)
        invested_eur          REAL NOT NULL,           -- Kumulierte Anschaffungskosten
        wert_eur              REAL,                    -- Marktwert (anzahl * kurs), NULL wenn kurs NULL
        gewinn_eur            REAL,                    -- wert_eur - invested_eur
        gewinn_pct            REAL,                    -- Gewinn in %, NULL wenn invested_eur = 0
        daily_total_wert      REAL,                    -- Gesamtwert aller Positionen an diesem Tag
        daily_total_invested  REAL NOT NULL,           -- Gesamtanschaffungskosten an diesem Tag
        daily_total_gewinn    REAL,                    -- Gesamtgewinn an diesem Tag
        created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(datum, wkn),
        FOREIGN KEY (wkn) REFERENCES securities(wkn)
    );

    CREATE INDEX IF NOT EXISTS idx_daily_invested_datum  ON daily_invested(datum);
    CREATE INDEX IF NOT EXISTS idx_daily_invested_wkn    ON daily_invested(wkn, datum);
    CREATE INDEX IF NOT EXISTS idx_daily_gains_datum     ON daily_gains(datum);
    CREATE INDEX IF NOT EXISTS idx_daily_gains_wkn       ON daily_gains(wkn, datum);
    """)
    conn.commit()
    conn.close()

    # Migration: importiere Altdaten in die neuen Tabellen
    from .services.migrate_legacy import run_migration
    from .services.daily_snapshots import calculate_daily_snapshots

    conn = get_db()
    try:
        run_migration(conn)
        print("Berechne tägliche Snapshots...")
        calculate_daily_snapshots(conn)
    finally:
        conn.close()
