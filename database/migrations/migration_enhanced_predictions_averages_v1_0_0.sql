-- ===============================================================================
-- Enhanced Predictions Averages Migration v1.0.0
-- Erweitert die PostgreSQL-Datenbank um Mittelwert-Berechnungen für Vorhersage-Zeiträume
-- 
-- CLEAN ARCHITECTURE PRINCIPLE:
-- - Single Responsibility: Nur Mittelwert-Berechnungen für Vorhersagen
-- - Performance-Optimiert: Materialized Views für < 50ms Query-Zeit
-- - Zero-Downtime: Kompatibel mit bestehenden Systemen
-- 
-- Autor: Claude Code Database Schema Enhancement Agent
-- Datum: 26. August 2025
-- Version: 1.0.0
-- ===============================================================================

-- ===============================================================================
-- PHASE 1: Schema-Erweiterung für soll_ist_gewinn_tracking
-- ===============================================================================

-- Neue Mittelwert-Spalten hinzufügen
ALTER TABLE soll_ist_gewinn_tracking 
ADD COLUMN IF NOT EXISTS avg_prediction_1w DECIMAL(12,4),
ADD COLUMN IF NOT EXISTS avg_prediction_1m DECIMAL(12,4),
ADD COLUMN IF NOT EXISTS avg_prediction_3m DECIMAL(12,4),
ADD COLUMN IF NOT EXISTS avg_prediction_12m DECIMAL(12,4);

-- Zusätzliche Metadaten für Mittelwert-Berechnungen
ALTER TABLE soll_ist_gewinn_tracking 
ADD COLUMN IF NOT EXISTS avg_calculation_date TIMESTAMP,
ADD COLUMN IF NOT EXISTS avg_sample_count_1w INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS avg_sample_count_1m INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS avg_sample_count_3m INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS avg_sample_count_12m INTEGER DEFAULT 0;

-- Kommentare für bessere Dokumentation
COMMENT ON COLUMN soll_ist_gewinn_tracking.avg_prediction_1w IS 'Durchschnitt der letzten 7 Tage Vorhersagen';
COMMENT ON COLUMN soll_ist_gewinn_tracking.avg_prediction_1m IS 'Durchschnitt der letzten 30 Tage Vorhersagen';
COMMENT ON COLUMN soll_ist_gewinn_tracking.avg_prediction_3m IS 'Durchschnitt der letzten 90 Tage Vorhersagen';
COMMENT ON COLUMN soll_ist_gewinn_tracking.avg_prediction_12m IS 'Durchschnitt der letzten 365 Tage Vorhersagen';

-- ===============================================================================
-- PHASE 2: Performance-Optimierte Indizes für neue Spalten
-- ===============================================================================

-- Index für Mittelwert-Abfragen nach Symbol und Zeitraum
CREATE INDEX IF NOT EXISTS idx_soll_ist_avg_symbol_date 
    ON soll_ist_gewinn_tracking (symbol, datum DESC) 
    WHERE avg_prediction_1w IS NOT NULL;

-- Index für Mittelwert-Berechnungen (Zeitfenster-Queries)
CREATE INDEX IF NOT EXISTS idx_soll_ist_avg_calculation 
    ON soll_ist_gewinn_tracking (avg_calculation_date DESC, symbol);

-- Composite Index für Performance-Analysen
CREATE INDEX IF NOT EXISTS idx_soll_ist_avg_performance 
    ON soll_ist_gewinn_tracking (symbol, datum DESC) 
    INCLUDE (avg_prediction_1w, avg_prediction_1m, avg_prediction_3m, avg_prediction_12m);

-- ===============================================================================
-- PHASE 3: Stored Functions für Mittelwert-Berechnungen
-- ===============================================================================

-- Funktion zur Berechnung der gleitenden Durchschnitte
CREATE OR REPLACE FUNCTION calculate_prediction_averages(
    p_symbol VARCHAR(10),
    p_target_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    avg_1w DECIMAL(12,4),
    avg_1m DECIMAL(12,4), 
    avg_3m DECIMAL(12,4),
    avg_12m DECIMAL(12,4),
    samples_1w INTEGER,
    samples_1m INTEGER,
    samples_3m INTEGER,
    samples_12m INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        -- 1 Woche Durchschnitt (7 Tage)
        AVG(CASE WHEN datum >= p_target_date - INTERVAL '7 days' 
                 THEN soll_gewinn_1w END)::DECIMAL(12,4) as avg_1w,
        -- 1 Monat Durchschnitt (30 Tage)  
        AVG(CASE WHEN datum >= p_target_date - INTERVAL '30 days' 
                 THEN soll_gewinn_1m END)::DECIMAL(12,4) as avg_1m,
        -- 3 Monate Durchschnitt (90 Tage)
        AVG(CASE WHEN datum >= p_target_date - INTERVAL '90 days' 
                 THEN soll_gewinn_3m END)::DECIMAL(12,4) as avg_3m,
        -- 12 Monate Durchschnitt (365 Tage)
        AVG(CASE WHEN datum >= p_target_date - INTERVAL '365 days' 
                 THEN soll_gewinn_12m END)::DECIMAL(12,4) as avg_12m,
                 
        -- Sample Counts für Validierung
        COUNT(CASE WHEN datum >= p_target_date - INTERVAL '7 days' 
                   AND soll_gewinn_1w IS NOT NULL THEN 1 END)::INTEGER as samples_1w,
        COUNT(CASE WHEN datum >= p_target_date - INTERVAL '30 days' 
                   AND soll_gewinn_1m IS NOT NULL THEN 1 END)::INTEGER as samples_1m,
        COUNT(CASE WHEN datum >= p_target_date - INTERVAL '90 days' 
                   AND soll_gewinn_3m IS NOT NULL THEN 1 END)::INTEGER as samples_3m,
        COUNT(CASE WHEN datum >= p_target_date - INTERVAL '365 days' 
                   AND soll_gewinn_12m IS NOT NULL THEN 1 END)::INTEGER as samples_12m
    FROM soll_ist_gewinn_tracking
    WHERE symbol = p_symbol
      AND datum <= p_target_date
      AND datum >= p_target_date - INTERVAL '365 days'; -- Optimiert: Nur relevante Zeitspanne
END;
$$ LANGUAGE plpgsql;

-- Funktion zum Update der Mittelwerte für ein Symbol
CREATE OR REPLACE FUNCTION update_prediction_averages(
    p_symbol VARCHAR(10),
    p_datum DATE DEFAULT CURRENT_DATE
)
RETURNS BOOLEAN AS $$
DECLARE
    v_averages RECORD;
BEGIN
    -- Berechne neue Mittelwerte
    SELECT * INTO v_averages 
    FROM calculate_prediction_averages(p_symbol, p_datum);
    
    -- Update des Records
    UPDATE soll_ist_gewinn_tracking 
    SET 
        avg_prediction_1w = v_averages.avg_1w,
        avg_prediction_1m = v_averages.avg_1m,
        avg_prediction_3m = v_averages.avg_3m,
        avg_prediction_12m = v_averages.avg_12m,
        avg_sample_count_1w = v_averages.samples_1w,
        avg_sample_count_1m = v_averages.samples_1m,
        avg_sample_count_3m = v_averages.samples_3m,
        avg_sample_count_12m = v_averages.samples_12m,
        avg_calculation_date = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE symbol = p_symbol 
      AND datum = p_datum;
      
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Batch-Update Funktion für alle Symbole
CREATE OR REPLACE FUNCTION update_all_prediction_averages(
    p_datum DATE DEFAULT CURRENT_DATE
)
RETURNS INTEGER AS $$
DECLARE
    v_symbol VARCHAR(10);
    v_updated_count INTEGER := 0;
BEGIN
    -- Loop durch alle einzigartigen Symbole für das Datum
    FOR v_symbol IN 
        SELECT DISTINCT symbol 
        FROM soll_ist_gewinn_tracking 
        WHERE datum = p_datum
    LOOP
        IF update_prediction_averages(v_symbol, p_datum) THEN
            v_updated_count := v_updated_count + 1;
        END IF;
    END LOOP;
    
    RETURN v_updated_count;
END;
$$ LANGUAGE plpgsql;

-- ===============================================================================
-- PHASE 4: Automatische Trigger für kontinuierliche Updates
-- ===============================================================================

-- Trigger-Funktion für automatische Mittelwert-Updates
CREATE OR REPLACE FUNCTION trigger_update_prediction_averages()
RETURNS TRIGGER AS $$
BEGIN
    -- Update Mittelwerte wenn SOLL-Gewinn Spalten geändert werden
    IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') AND (
        NEW.soll_gewinn_1w IS DISTINCT FROM OLD.soll_gewinn_1w OR
        NEW.soll_gewinn_1m IS DISTINCT FROM OLD.soll_gewinn_1m OR  
        NEW.soll_gewinn_3m IS DISTINCT FROM OLD.soll_gewinn_3m OR
        NEW.soll_gewinn_12m IS DISTINCT FROM OLD.soll_gewinn_12m OR
        TG_OP = 'INSERT'
    ) THEN
        PERFORM update_prediction_averages(NEW.symbol, NEW.datum);
        
        -- Update auch abhängige Datensätze (letzte 365 Tage)
        -- Nur wenn genügend Änderungen für Performance-Optimierung
        IF (random() < 0.1) THEN -- 10% Chance für Batch-Update
            PERFORM update_prediction_averages(
                s.symbol, 
                s.datum
            )
            FROM (
                SELECT DISTINCT symbol, datum 
                FROM soll_ist_gewinn_tracking
                WHERE symbol = NEW.symbol
                  AND datum >= NEW.datum - INTERVAL '30 days'
                  AND datum <= NEW.datum
                  AND (avg_calculation_date IS NULL OR 
                       avg_calculation_date < CURRENT_TIMESTAMP - INTERVAL '1 hour')
                LIMIT 10 -- Performance-Limit
            ) s;
        END IF;
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Trigger erstellen
CREATE TRIGGER trigger_prediction_averages_update
    AFTER INSERT OR UPDATE ON soll_ist_gewinn_tracking
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_prediction_averages();

-- ===============================================================================
-- PHASE 5: Performance-optimierte Views
-- ===============================================================================

-- View für Mittelwert-Übersicht mit Performance-Metriken
CREATE OR REPLACE VIEW v_prediction_averages_summary AS
SELECT 
    symbol,
    datum,
    unternehmen,
    
    -- Aktuelle Vorhersagen
    soll_gewinn_1w,
    soll_gewinn_1m, 
    soll_gewinn_3m,
    soll_gewinn_12m,
    
    -- Mittelwerte
    avg_prediction_1w,
    avg_prediction_1m,
    avg_prediction_3m, 
    avg_prediction_12m,
    
    -- Abweichungen von Mittelwerten (Volatilität Indikator)
    CASE WHEN avg_prediction_1w IS NOT NULL 
         THEN ABS(soll_gewinn_1w - avg_prediction_1w) 
         ELSE NULL 
    END as deviation_1w,
    CASE WHEN avg_prediction_1m IS NOT NULL 
         THEN ABS(soll_gewinn_1m - avg_prediction_1m) 
         ELSE NULL 
    END as deviation_1m,
    CASE WHEN avg_prediction_3m IS NOT NULL 
         THEN ABS(soll_gewinn_3m - avg_prediction_3m) 
         ELSE NULL 
    END as deviation_3m,
    CASE WHEN avg_prediction_12m IS NOT NULL 
         THEN ABS(soll_gewinn_12m - avg_prediction_12m) 
         ELSE NULL 
    END as deviation_12m,
    
    -- Sample Sizes für Validierung
    avg_sample_count_1w,
    avg_sample_count_1m,
    avg_sample_count_3m,
    avg_sample_count_12m,
    
    -- Trend Analysis (Vergleich aktuell vs Mittelwert)
    CASE 
        WHEN avg_prediction_1w IS NULL THEN 'INSUFFICIENT_DATA'
        WHEN soll_gewinn_1w > avg_prediction_1w * 1.05 THEN 'ABOVE_AVERAGE'
        WHEN soll_gewinn_1w < avg_prediction_1w * 0.95 THEN 'BELOW_AVERAGE' 
        ELSE 'NEAR_AVERAGE'
    END as trend_1w,
    
    -- Metadata
    avg_calculation_date,
    created_at,
    updated_at
    
FROM soll_ist_gewinn_tracking
ORDER BY symbol, datum DESC;

-- Materialized View für Performance-kritische Abfragen
CREATE MATERIALIZED VIEW mv_prediction_averages_fast AS
SELECT 
    symbol,
    COUNT(*) as total_records,
    MAX(datum) as latest_date,
    
    -- Aktuelle Mittelwerte (neueste Datensätze)
    FIRST_VALUE(avg_prediction_1w) OVER (
        PARTITION BY symbol 
        ORDER BY datum DESC, updated_at DESC
        ROWS UNBOUNDED PRECEDING
    ) as current_avg_1w,
    FIRST_VALUE(avg_prediction_1m) OVER (
        PARTITION BY symbol 
        ORDER BY datum DESC, updated_at DESC
        ROWS UNBOUNDED PRECEDING
    ) as current_avg_1m,
    FIRST_VALUE(avg_prediction_3m) OVER (
        PARTITION BY symbol 
        ORDER BY datum DESC, updated_at DESC
        ROWS UNBOUNDED PRECEDING
    ) as current_avg_3m,
    FIRST_VALUE(avg_prediction_12m) OVER (
        PARTITION BY symbol 
        ORDER BY datum DESC, updated_at DESC
        ROWS UNBOUNDED PRECEDING
    ) as current_avg_12m,
    
    -- Trend-Metriken (30-Tage Volatilität der Mittelwerte)
    STDDEV(avg_prediction_1m) OVER (
        PARTITION BY symbol 
        ORDER BY datum DESC
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) as volatility_1m,
    
    -- Performance-Indikatoren
    AVG(CASE WHEN avg_sample_count_1w > 0 THEN avg_sample_count_1w END) as avg_sample_quality_1w,
    
    MAX(avg_calculation_date) as last_calculation
    
FROM soll_ist_gewinn_tracking
WHERE avg_prediction_1w IS NOT NULL
   OR avg_prediction_1m IS NOT NULL
   OR avg_prediction_3m IS NOT NULL
   OR avg_prediction_12m IS NOT NULL
GROUP BY symbol
ORDER BY symbol;

-- Index für Materialized View
CREATE UNIQUE INDEX mv_prediction_averages_fast_symbol_idx 
    ON mv_prediction_averages_fast (symbol);

-- ===============================================================================
-- PHASE 6: Wartungs-Funktionen
-- ===============================================================================

-- Funktion zum Refresh der Materialized View
CREATE OR REPLACE FUNCTION refresh_prediction_averages_materialized_view()
RETURNS BOOLEAN AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_prediction_averages_fast;
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        -- Fallback: Non-concurrent refresh
        REFRESH MATERIALIZED VIEW mv_prediction_averages_fast;
        RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Funktion für Datenbereinigung (alte Berechnungen)
CREATE OR REPLACE FUNCTION cleanup_old_average_calculations(
    p_keep_days INTEGER DEFAULT 365
)
RETURNS INTEGER AS $$
DECLARE
    v_cutoff_date DATE;
    v_deleted_count INTEGER;
BEGIN
    v_cutoff_date := CURRENT_DATE - p_keep_days;
    
    -- Reset alte avg_calculation_date für Neuberechnung
    UPDATE soll_ist_gewinn_tracking 
    SET avg_calculation_date = NULL
    WHERE avg_calculation_date < v_cutoff_date::timestamp
      AND datum >= v_cutoff_date;
      
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ===============================================================================
-- PHASE 7: Initiale Datenberechnung für bestehende Records
-- ===============================================================================

-- Berechne Mittelwerte für alle existierenden Datensätze
DO $$
DECLARE
    v_symbol VARCHAR(10);
    v_datum DATE;
    v_count INTEGER := 0;
    v_total INTEGER;
BEGIN
    -- Zähle Gesamtanzahl für Progress-Tracking
    SELECT COUNT(*) INTO v_total 
    FROM soll_ist_gewinn_tracking;
    
    RAISE NOTICE 'Starting initial average calculation for % records', v_total;
    
    -- Loop durch alle Records
    FOR v_symbol, v_datum IN 
        SELECT DISTINCT symbol, datum 
        FROM soll_ist_gewinn_tracking 
        WHERE (soll_gewinn_1w IS NOT NULL OR 
               soll_gewinn_1m IS NOT NULL OR 
               soll_gewinn_3m IS NOT NULL OR 
               soll_gewinn_12m IS NOT NULL)
        ORDER BY datum DESC, symbol -- Neueste zuerst für bessere Performance
    LOOP
        PERFORM update_prediction_averages(v_symbol, v_datum);
        v_count := v_count + 1;
        
        -- Progress-Benachrichtigung alle 100 Records
        IF v_count % 100 = 0 THEN
            RAISE NOTICE 'Processed % of % records (%.1f%%)', 
                v_count, v_total, (v_count::FLOAT / v_total * 100);
        END IF;
    END LOOP;
    
    RAISE NOTICE 'Initial calculation completed: % records processed', v_count;
END $$;

-- Erstelle initiale Materialized View
SELECT refresh_prediction_averages_materialized_view();

-- ===============================================================================
-- PHASE 8: Performance-Tests und Validierung
-- ===============================================================================

-- Test-Abfrage: Mittelwerte für ein Symbol
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM v_prediction_averages_summary 
WHERE symbol = 'AAPL' 
  AND datum >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY datum DESC;

-- Test-Abfrage: Schnelle Materialized View
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM mv_prediction_averages_fast 
WHERE symbol = 'AAPL';

-- ===============================================================================
-- MIGRATION SUCCESS MESSAGE
-- ===============================================================================

SELECT 
    'Enhanced Predictions Averages Migration v1.0.0 erfolgreich abgeschlossen!' as status,
    COUNT(DISTINCT symbol) as total_symbols_processed,
    COUNT(*) as total_records_enhanced,
    COUNT(CASE WHEN avg_prediction_1w IS NOT NULL THEN 1 END) as records_with_avg_1w,
    COUNT(CASE WHEN avg_prediction_1m IS NOT NULL THEN 1 END) as records_with_avg_1m,
    COUNT(CASE WHEN avg_prediction_3m IS NOT NULL THEN 1 END) as records_with_avg_3m,
    COUNT(CASE WHEN avg_prediction_12m IS NOT NULL THEN 1 END) as records_with_avg_12m
FROM soll_ist_gewinn_tracking;

-- Performance-Benchmark
SELECT 
    'Performance-Benchmark' as test_type,
    pg_size_pretty(pg_total_relation_size('soll_ist_gewinn_tracking')) as table_size,
    pg_size_pretty(pg_total_relation_size('mv_prediction_averages_fast')) as materialized_view_size,
    (SELECT COUNT(*) FROM soll_ist_gewinn_tracking) as total_records;