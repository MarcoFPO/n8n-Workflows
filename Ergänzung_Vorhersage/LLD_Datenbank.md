# LLD: Datenbank für ML-Integration in Event-Driven Architecture

---

### 1. Zielsetzung und Geltungsbereich

**ÜBERARBEITET FÜR INTEGRATION**: Dieses Dokument beschreibt die technische Konzeption der **erweiterten PostgreSQL-Datenbank** für die ML-Integration in das bestehende Event-Driven aktienanalyse-ökosystem.

**Integration in bestehende Architektur:**
*   **Bestehende Event-Store-Datenbank**: Erweitern um ML-spezifische Tabellen
*   **PostgreSQL mit TimescaleDB**: Bereits produktiv auf 10.1.1.174
*   **Event-Bus Integration**: ML-Events in bestehende Event-Store-Architektur
*   **Service-übergreifend**: ML-Daten für alle 8 Microservices verfügbar

**Erweiterte Verwendungszwecke:**
*   **Echtzeit-Feature-Engineering**: Über Data Processing Service (Port 8017)
*   **Live-Prediction-Serving**: Über ML Analytics Service (Port 8019)  
*   **Event-Correlation**: ML-Events mit Trading/Analysis-Events verknüpft
*   **Performance-Monitoring**: Real-time ML-Performance-Tracking

### 2. Technologiewahl

*   **Datenbanksystem:** **PostgreSQL** (Version 14 oder höher).
    *   **Begründung:** Robust, Open-Source, exzellente SQL-Unterstützung, hohe Erweiterbarkeit und bewährt für komplexe Datenmodelle.
*   **Erweiterung:** **TimescaleDB**.
    *   **Begründung:** TimescaleDB ist eine Open-Source-Erweiterung für PostgreSQL, die es in eine hochperformante Zeitreihen-Datenbank verwandelt. Dies bietet entscheidende Vorteile:
        *   **Automatische Partitionierung:** Zeitreihen-Tabellen (Hypertables) werden intern nach Zeit partitioniert, was die Abfragegeschwindigkeit für Zeitfenster-Queries (z.B. "gib mir alle Daten der letzten 60 Tage") drastisch erhöht.
        *   **Effiziente Speicherung:** Optimiert für die Speicherung von Zeitreihendaten.
        *   **Spezialisierte Funktionen:** Bietet nützliche Funktionen für die Zeitreihen-Analyse.

### 3. Logisches Datenmodell (Schema Design)

Das Schema ist in zwei Bereiche unterteilt: **Rohdaten-Tabellen** (Staging Area) und **Feature-Tabellen** (Verarbeitete Daten).

#### 3.1 Stammdaten-Tabellen

Diese Tabellen speichern Metadaten zu den gehandelten Wertpapieren.

**`exchanges`**
*   Speichert Informationen über die Börsenplätze.
*   **Spalten:**
    *   `exchange_id` (SERIAL, PRIMARY KEY)
    *   `name` (VARCHAR(100), NOT NULL, UNIQUE) - z.B. "XETRA"
    *   `country_code` (VARCHAR(2), NOT NULL) - z.B. "DE"

**`securities`**
*   Speichert die einzelnen Wertpapiere.
*   **Spalten:**
    *   `security_id` (SERIAL, PRIMARY KEY)
    *   `ticker` (VARCHAR(20), NOT NULL) - z.B. "VOW3.DE"
    *   `exchange_id` (INTEGER, FOREIGN KEY an `exchanges.exchange_id`)
    *   `name` (VARCHAR(255)) - z.B. "Volkswagen AG"
    *   `currency` (VARCHAR(3), NOT NULL) - z.B. "EUR"
    *   UNIQUE (`ticker`, `exchange_id`)

---

#### 3.2 Rohdaten-Tabellen (Staging)

Diese Tabellen nehmen die 1:1-Daten von den externen APIs auf.

**`raw_price_data`** (TimescaleDB Hypertable)
*   Speichert tägliche OHLCV-Daten.
*   **Spalten:**
    *   `timestamp` (TIMESTAMPTZ, NOT NULL)
    *   `security_id` (INTEGER, FOREIGN KEY an `securities.security_id`)
    *   `open` (NUMERIC(19, 4))
    *   `high` (NUMERIC(19, 4))
    *   `low` (NUMERIC(19, 4))
    *   `close` (NUMERIC(19, 4))
    *   `volume` (BIGINT)
    *   PRIMARY KEY (`timestamp`, `security_id`)

**`raw_sentiment_articles`**
*   Speichert einzelne Nachrichten, Tweets etc.
*   **Spalten:**
    *   `article_id` (BIGSERIAL, PRIMARY KEY)
    *   `security_id` (INTEGER, FOREIGN KEY an `securities.security_id`)
    *   `published_at` (TIMESTAMPTZ, NOT NULL)
    *   `source` (VARCHAR(50)) - z.B. "newsapi", "reddit"
    *   `language` (VARCHAR(5)) - z.B. "de", "en"
    *   `title` (TEXT)
    *   `content` (TEXT)

**`raw_fundamental_reports`**
*   Speichert Kennzahlen aus Quartals-/Jahresberichten.
*   **Spalten:**
    *   `report_id` (BIGSERIAL, PRIMARY KEY)
    *   `security_id` (INTEGER, FOREIGN KEY an `securities.security_id`)
    *   `report_date` (DATE, NOT NULL) - Enddatum des Berichtszeitraums
    *   `publish_date` (DATE, NOT NULL) - Veröffentlichungsdatum
    *   `metric_key` (VARCHAR(100), NOT NULL) - z.B. "totalRevenue", "earningsPerShare"
    *   `value` (NUMERIC(22, 4))
    *   `currency` (VARCHAR(3))

**`raw_macro_indicators`** (TimescaleDB Hypertable)
*   Speichert makroökonomische Indikatoren.
*   **Spalten:**
    *   `timestamp` (TIMESTAMPTZ, NOT NULL)
    *   `indicator_key` (VARCHAR(50), NOT NULL) - z.B. "VIXCLS", "CPIAUCSL"
    *   `region` (VARCHAR(50), NOT NULL) - z.B. "USA", "EUROZONE"
    *   `value` (NUMERIC(18, 4))
    *   PRIMARY KEY (`timestamp`, `indicator_key`, `region`)

---

#### 3.3 ML-Feature-Tabellen (Event-Bus Integration)

**ERWEITERT FÜR EVENT-DRIVEN ARCHITECTURE**: Diese Tabellen enthalten ML-spezifische Features mit Event-Correlation für das bestehende Event-Bus-System.

**`ml_features_technical_daily`** (TimescaleDB Hypertable)
*   **Erweiterte Spalten für Event-Integration:**
    *   `timestamp` (TIMESTAMPTZ, NOT NULL)
    *   `symbol` (VARCHAR(20), NOT NULL) -- Direkte Symbol-Referenz
    *   `security_id` (INTEGER, FOREIGN KEY an `securities.security_id`)
    
    *   **Momentum Features:**
    *   `rsi_14` (NUMERIC(8,4))
    *   `macd_signal_12_26_9` (NUMERIC(8,4))
    *   `macd_histogram_12_26_9` (NUMERIC(8,4))
    *   `stoch_k_14_3` (NUMERIC(8,4))
    *   `stoch_d_14_3` (NUMERIC(8,4))
    
    *   **Trend Features:**
    *   `sma_20` (NUMERIC(12,4))
    *   `sma_50` (NUMERIC(12,4))
    *   `sma_200` (NUMERIC(12,4))
    *   `ema_20` (NUMERIC(12,4))
    *   `ema_50` (NUMERIC(12,4))
    
    *   **Volatility Features:**
    *   `bb_upper_20_2` (NUMERIC(12,4))
    *   `bb_middle_20_2` (NUMERIC(12,4))
    *   `bb_lower_20_2` (NUMERIC(12,4))
    *   `atr_14` (NUMERIC(8,4))
    
    *   **Volume Features:**
    *   `volume_sma_20` (BIGINT)
    *   `volume_ratio` (NUMERIC(6,4))
    
    *   **Price Action Features:**
    *   `daily_return` (NUMERIC(8,6))
    *   `weekly_return` (NUMERIC(8,6))
    *   `high_low_ratio` (NUMERIC(8,4))
    
    *   **Event-Integration:**
    *   `event_correlation_id` (UUID) -- Verknüpfung mit Event-Store
    *   `created_at` (TIMESTAMPTZ DEFAULT NOW())
    *   `updated_by_service` (VARCHAR(50)) -- Service, das Update durchgeführt hat
    
    *   PRIMARY KEY (`timestamp`, `symbol`)
    *   INDEX (`symbol`, `timestamp`)
    *   INDEX (`event_correlation_id`)

**`ml_features_sentiment_daily`** (TimescaleDB Hypertable)
*   **Event-Enhanced Spalten:**
    *   `timestamp` (TIMESTAMPTZ, NOT NULL)
    *   `symbol` (VARCHAR(20), NOT NULL)
    *   `security_id` (INTEGER, FOREIGN KEY an `securities.security_id`)
    
    *   **Sentiment Metrics:**
    *   `avg_sentiment_score` (NUMERIC(5, 4)) -- -1 bis +1
    *   `sentiment_volume` (INTEGER) -- Anzahl analysierter Artikel/Posts
    *   `positive_ratio` (NUMERIC(5, 4)) -- Anteil positiver Mentions
    *   `negative_ratio` (NUMERIC(5, 4)) -- Anteil negativer Mentions
    *   `neutral_ratio` (NUMERIC(5, 4)) -- Anteil neutraler Mentions
    
    *   **Source-specific Sentiment:**
    *   `news_sentiment_avg` (NUMERIC(5, 4)) -- Durchschnitt Nachrichten
    *   `social_sentiment_avg` (NUMERIC(5, 4)) -- Durchschnitt Social Media
    *   `analyst_sentiment_encoded` (INTEGER) -- 1=Buy, 0=Hold, -1=Sell
    
    *   **Event-Integration:**
    *   `event_correlation_id` (UUID)
    *   `source_events` (JSONB) -- IDs der zugrundeliegenden Sentiment-Events
    *   `created_at` (TIMESTAMPTZ DEFAULT NOW())
    
    *   PRIMARY KEY (`timestamp`, `symbol`)

**`ml_features_fundamental_macro_daily`** (TimescaleDB Hypertable)
*   **Event-Enhanced Spalten:**
    *   `timestamp` (TIMESTAMPTZ, NOT NULL)
    *   `symbol` (VARCHAR(20), NOT NULL)
    *   `security_id` (INTEGER, FOREIGN KEY an `securities.security_id`)
    
    *   **Fundamental Features (Forward-filled):**
    *   `eps_ttm` (NUMERIC(12,4)) -- Earnings per Share TTM
    *   `pe_ratio` (NUMERIC(8,4)) -- Price-to-Earnings Ratio
    *   `pb_ratio` (NUMERIC(8,4)) -- Price-to-Book Ratio
    *   `debt_to_equity` (NUMERIC(8,4))
    *   `revenue_growth_yoy` (NUMERIC(8,4))
    *   `profit_margin` (NUMERIC(8,4))
    
    *   **Macro Features:**
    *   `vix_level` (NUMERIC(8,4)) -- Volatility Index
    *   `fed_rate` (NUMERIC(6,4)) -- Federal Funds Rate
    *   `inflation_rate_cpi` (NUMERIC(6,4)) -- Consumer Price Index
    *   `unemployment_rate` (NUMERIC(6,4))
    *   `gdp_growth_rate` (NUMERIC(6,4))
    
    *   **Event-Integration:**
    *   `event_correlation_id` (UUID)
    *   `fundamental_data_age_days` (INTEGER) -- Alter der letzten Fundamental-Daten
    *   `macro_data_freshness` (JSONB) -- Freshness-Status jedes Makro-Indikators
    *   `created_at` (TIMESTAMPTZ DEFAULT NOW())
    
    *   PRIMARY KEY (`timestamp`, `symbol`)

---

#### 3.4 ML-Prediction und Model-Management Tabellen

**`ml_predictions`** (TimescaleDB Hypertable)
*   **Zentrale Prediction-Storage mit Event-Integration:**
    *   `prediction_id` (UUID PRIMARY KEY DEFAULT gen_random_uuid())
    *   `symbol` (VARCHAR(20), NOT NULL)
    *   `prediction_timestamp` (TIMESTAMPTZ, NOT NULL)
    *   `model_type` (VARCHAR(50), NOT NULL) -- 'technical', 'sentiment', 'fundamental', 'ensemble'
    *   `horizon_days` (INTEGER, NOT NULL) -- 7, 30, 150, 365
    
    *   **Prediction Data:**
    *   `prediction_values` (JSONB, NOT NULL) -- [day1_pct, day2_pct, ..., dayN_pct]
    *   `confidence_score` (NUMERIC(5,4)) -- 0.0 bis 1.0
    *   `feature_importance` (JSONB) -- Top-Features für diese Prediction
    
    *   **Model Metadata:**
    *   `model_version` (VARCHAR(50), NOT NULL)
    *   `model_id` (UUID REFERENCES ml_model_metadata(model_id))
    
    *   **Event-Integration:**
    *   `event_correlation_id` (UUID, NOT NULL) -- Event, das Prediction ausgelöst hat
    *   `trigger_event_type` (VARCHAR(100)) -- z.B. 'market.data.updated'
    *   `source_service` (VARCHAR(50)) -- Service, das Prediction generiert hat
    
    *   **Lifecycle:**
    *   `created_at` (TIMESTAMPTZ DEFAULT NOW())
    *   `expires_at` (TIMESTAMPTZ) -- Automatische Bereinigung alter Predictions
    *   `validated_at` (TIMESTAMPTZ) -- Zeitpunkt der Validierung gegen Realität
    *   `validation_result` (JSONB) -- Accuracy-Metriken der Validierung
    
    *   INDEX (`symbol`, `prediction_timestamp`)
    *   INDEX (`model_type`, `horizon_days`)
    *   INDEX (`event_correlation_id`)
    *   INDEX (`expires_at`) -- Für Cleanup-Jobs

**`ml_model_metadata`**
*   **Model-Lifecycle-Management:**
    *   `model_id` (UUID PRIMARY KEY DEFAULT gen_random_uuid())
    *   `model_type` (VARCHAR(50), NOT NULL)
    *   `model_version` (VARCHAR(50), NOT NULL) -- Folgt Modul-Versioning: v1.0.0_20250817
    *   `horizon_days` (INTEGER, NOT NULL)
    
    *   **Configuration:**
    *   `architecture_config` (JSONB, NOT NULL) -- Model-Architektur-Details
    *   `training_config` (JSONB, NOT NULL) -- Training-Parameter
    *   `hyperparameters` (JSONB, NOT NULL) -- Optimierte Hyperparameter
    
    *   **Performance Tracking:**
    *   `training_metrics` (JSONB) -- Training-Performance
    *   `validation_metrics` (JSONB) -- Validation-Performance
    *   `production_metrics` (JSONB) -- Live-Performance-Updates
    
    *   **Storage:**
    *   `model_file_path` (VARCHAR(500)) -- Pfad zur .h5/.pkl Datei
    *   `scaler_file_path` (VARCHAR(500)) -- Pfad zum Feature-Scaler
    *   `artifact_checksum` (VARCHAR(64)) -- SHA256 für Integrität
    
    *   **Lifecycle:**
    *   `status` (VARCHAR(20) DEFAULT 'training') -- 'training', 'active', 'deprecated', 'failed'
    *   `deployed_at` (TIMESTAMPTZ) -- Deployment-Zeitpunkt
    *   `deprecated_at` (TIMESTAMPTZ) -- Ablösungs-Zeitpunkt
    *   `created_at` (TIMESTAMPTZ DEFAULT NOW())
    
    *   UNIQUE (`model_type`, `model_version`, `horizon_days`)

### 4. Physisches Datenmodell & Indizierung

*   **Hypertables:** Alle Tabellen mit einer `timestamp`-Spalte, die Zeitreihendaten speichern (`raw_price_data`, `raw_macro_indicators`, `features_*_daily`), werden mit dem Befehl `create_hypertable()` in TimescaleDB-Hypertables umgewandelt.
    *   `SELECT create_hypertable('raw_price_data', 'timestamp');`
*   **Indizes:**
    *   Zusätzlich zu den Primärschlüsseln werden Indizes auf allen `security_id`-Fremdschlüsseln erstellt, um Abfragen für ein einzelnes Wertpapier zu beschleunigen.
    *   Für die `raw_sentiment_articles`-Tabelle wird ein Index auf `(security_id, published_at)` erstellt.

### 5. Datenfluss im Geltungsbereich

1.  **Datengewinnung (3.1):** Tägliche Skripte rufen die externen APIs ab und schreiben die unveränderten Daten in die `raw_*`-Tabellen.
2.  **Datenvorverarbeitung (3.2):**
    *   Ein separates Set von Skripten liest Daten aus den `raw_*`-Tabellen.
    *   Diese Skripte führen Bereinigungen, Berechnungen (technische Indikatoren, Sentiment-Scores), Aggregationen und das Forward-Filling durch.
    *   Die Ergebnisse werden in die `features_*_daily`-Tabellen geschrieben.
3.  **Modelltraining (3.3-3.5):**
    *   Die Trainings-Pipeline liest die finalen, aufbereiteten Daten aus den `features_*_daily`-Tabellen.
    *   Sie führt Joins über die `security_id` und `timestamp` aus, um den vollständigen Feature-Satz für das Training zu erstellen.
    *   Die Datenbank wird hier nur lesend genutzt.
