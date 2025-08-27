-- ===============================================================================
-- Enhanced Predictions Averages für KI-Prognosen GUI v1.0.0
-- Durchschnittswerte-Spalte für KI-Prognosen Interface
-- 
-- CLEAN ARCHITECTURE PRINCIPLE:
-- - Single Responsibility: Nur Durchschnittswerte-Berechnung für GUI
-- - Open/Closed: Erweiterbar ohne bestehende Funktionalität zu ändern
-- - Interface Segregation: Spezialisierte Views für GUI-Anforderungen
--
-- Anforderungen:
-- a) Durchschnittswerte pro Symbol und Zeitrahmen
-- b) Integration mit bestehender prediction_tracking_unified Tabelle
-- c) Performance-optimierte Queries für GUI-Darstellung
-- d) Timeline-Navigation kompatible Datenstruktur
--
-- Autor: Claude Code
-- Datum: 26. August 2025
-- Version: 1.0.0
-- ===============================================================================

-- ===============================================================================
-- DURCHSCHNITTSWERTE VIEW für KI-Prognosen GUI
-- ===============================================================================

-- Materialized View für Performance-optimierte Durchschnittswerte
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_ki_prognosen_averages AS
SELECT 
    symbol,
    company_name,
    horizon_type,
    horizon_days,
    
    -- Durchschnittswerte-Berechnung
    COUNT(*) as prediction_count,
    AVG(predicted_value) as avg_predicted_value,
    AVG(CASE WHEN actual_value IS NOT NULL THEN actual_value END) as avg_actual_value,
    AVG(CASE WHEN performance_accuracy IS NOT NULL THEN performance_accuracy END) as avg_accuracy,
    AVG(confidence_score) as avg_confidence,
    
    -- Zeitbereich für Timeline-Navigation
    MIN(calculation_date) as earliest_prediction,
    MAX(calculation_date) as latest_prediction,
    MIN(target_date) as earliest_target,
    MAX(target_date) as latest_target,
    
    -- Status-Übersicht
    COUNT(CASE WHEN status = 'evaluated' THEN 1 END) as evaluated_count,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
    
    -- Performance-Statistiken
    STDDEV(predicted_value) as predicted_value_stddev,
    MIN(predicted_value) as min_predicted_value,
    MAX(predicted_value) as max_predicted_value,
    
    -- Letzte Aktualisierung
    CURRENT_TIMESTAMP as last_updated

FROM prediction_tracking_unified
WHERE calculation_date >= CURRENT_DATE - INTERVAL '90 days'  -- Fokus auf letzten 90 Tage
GROUP BY symbol, company_name, horizon_type, horizon_days
HAVING COUNT(*) >= 3;  -- Mindestens 3 Vorhersagen für aussagekräftige Durchschnitte

-- Performance-Index für schnelle GUI-Abfragen
CREATE UNIQUE INDEX IF NOT EXISTS idx_averages_symbol_horizon 
ON mv_ki_prognosen_averages(symbol, horizon_type);

CREATE INDEX IF NOT EXISTS idx_averages_prediction_count 
ON mv_ki_prognosen_averages(prediction_count DESC);

-- ===============================================================================
-- GUI-OPTIMIERTE VIEW mit Durchschnittswerten
-- ===============================================================================

-- View für KI-Prognosen GUI mit integrierten Durchschnittswerten
CREATE OR REPLACE VIEW v_ki_prognosen_enhanced AS
SELECT 
    -- Basis-Vorhersagedaten
    pt.symbol,
    pt.company_name,
    pt.calculation_date,
    pt.target_date,
    pt.predicted_value,
    pt.actual_value,
    pt.performance_accuracy,
    pt.confidence_score,
    pt.horizon_type,
    pt.horizon_days,
    pt.status,
    
    -- Durchschnittswerte aus Materialized View
    avg.avg_predicted_value,
    avg.avg_actual_value,
    avg.avg_accuracy,
    avg.avg_confidence,
    avg.prediction_count,
    
    -- Abweichung vom Durchschnitt
    CASE 
        WHEN avg.avg_predicted_value IS NOT NULL 
        THEN pt.predicted_value - avg.avg_predicted_value
        ELSE NULL 
    END as deviation_from_avg,
    
    -- Relative Performance zum Durchschnitt
    CASE 
        WHEN avg.avg_predicted_value IS NOT NULL AND avg.avg_predicted_value != 0
        THEN ((pt.predicted_value - avg.avg_predicted_value) / ABS(avg.avg_predicted_value)) * 100
        ELSE NULL 
    END as relative_performance_percent,
    
    -- GUI-spezifische Formatierungen
    TO_CHAR(pt.calculation_date, 'DD.MM.YYYY HH24:MI') as formatted_calculation_date,
    TO_CHAR(pt.target_date, 'DD.MM.YYYY') as formatted_target_date,
    ROUND(pt.predicted_value, 2) as predicted_value_rounded,
    ROUND(avg.avg_predicted_value, 2) as avg_predicted_value_rounded,
    ROUND(pt.confidence_score * 100, 1) as confidence_percentage

FROM prediction_tracking_unified pt
LEFT JOIN mv_ki_prognosen_averages avg 
    ON pt.symbol = avg.symbol 
    AND pt.horizon_type = avg.horizon_type

WHERE pt.calculation_date >= CURRENT_DATE - INTERVAL '30 days'  -- GUI zeigt letzten Monat
ORDER BY pt.calculation_date DESC, pt.confidence_score DESC;

-- ===============================================================================
-- STORED FUNCTIONS für GUI-Backend
-- ===============================================================================

-- Funktion für KI-Prognosen mit Durchschnittswerten
CREATE OR REPLACE FUNCTION get_ki_prognosen_with_averages(
    p_timeframe VARCHAR(10) DEFAULT '1M',
    p_limit INTEGER DEFAULT 15,
    p_nav_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
RETURNS TABLE (
    symbol VARCHAR(10),
    company_name VARCHAR(255),
    calculation_date TIMESTAMP,
    target_date DATE,
    predicted_value DECIMAL(12,4),
    predicted_value_rounded DECIMAL(12,2),
    avg_predicted_value DECIMAL(12,4),
    avg_predicted_value_rounded DECIMAL(12,2),
    deviation_from_avg DECIMAL(12,4),
    relative_performance_percent DECIMAL(8,2),
    confidence_score DECIMAL(5,4),
    confidence_percentage DECIMAL(5,1),
    avg_confidence DECIMAL(5,4),
    prediction_count INTEGER,
    status VARCHAR(20),
    formatted_calculation_date TEXT,
    formatted_target_date TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.symbol,
        v.company_name,
        v.calculation_date,
        v.target_date,
        v.predicted_value,
        v.predicted_value_rounded,
        v.avg_predicted_value,
        v.avg_predicted_value_rounded,
        v.deviation_from_avg,
        v.relative_performance_percent,
        v.confidence_score,
        v.confidence_percentage,
        v.avg_confidence,
        v.prediction_count,
        v.status,
        v.formatted_calculation_date,
        v.formatted_target_date
    FROM v_ki_prognosen_enhanced v
    WHERE v.horizon_type = p_timeframe
    AND v.calculation_date <= p_nav_timestamp + INTERVAL '1 day'  -- Timeline-Navigation Support
    AND v.calculation_date >= p_nav_timestamp - INTERVAL '7 days'  -- Zeitfenster für Navigation
    ORDER BY v.predicted_value_rounded DESC, v.confidence_percentage DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Funktion für Durchschnittswerte-Übersicht
CREATE OR REPLACE FUNCTION get_averages_summary(
    p_timeframe VARCHAR(10) DEFAULT '1M'
)
RETURNS TABLE (
    symbol VARCHAR(10),
    company_name VARCHAR(255),
    horizon_type VARCHAR(10),
    avg_predicted_value DECIMAL(12,4),
    avg_actual_value DECIMAL(12,4),
    avg_accuracy DECIMAL(5,2),
    avg_confidence DECIMAL(5,4),
    prediction_count INTEGER,
    evaluated_count INTEGER,
    pending_count INTEGER,
    last_updated TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        avg.symbol,
        avg.company_name,
        avg.horizon_type,
        ROUND(avg.avg_predicted_value, 4) as avg_predicted_value,
        ROUND(avg.avg_actual_value, 4) as avg_actual_value,
        ROUND(avg.avg_accuracy, 2) as avg_accuracy,
        ROUND(avg.avg_confidence, 4) as avg_confidence,
        avg.prediction_count,
        avg.evaluated_count,
        avg.pending_count,
        avg.last_updated
    FROM mv_ki_prognosen_averages avg
    WHERE avg.horizon_type = p_timeframe
    ORDER BY avg.prediction_count DESC, avg.avg_confidence DESC;
END;
$$ LANGUAGE plpgsql;

-- ===============================================================================
-- REFRESH FUNCTION für Materialized View
-- ===============================================================================

-- Funktion zum Aktualisieren der Materialized View
CREATE OR REPLACE FUNCTION refresh_ki_prognosen_averages()
RETURNS VOID AS $$
BEGIN
    -- Refresh Materialized View
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_ki_prognosen_averages;
    
    -- Log Update
    INSERT INTO prediction_performance_metrics (
        symbol, horizon_type, metric_date,
        calculated_at
    ) VALUES (
        'SYSTEM', 'REFRESH', CURRENT_DATE,
        CURRENT_TIMESTAMP
    ) ON CONFLICT (symbol, horizon_type, metric_date) DO UPDATE SET
        calculated_at = EXCLUDED.calculated_at;
END;
$$ LANGUAGE plpgsql;

-- ===============================================================================
-- AUTOMATED REFRESH (Optional Cron Job Support)
-- ===============================================================================

-- Trigger für automatische Aktualisierung bei neuen Vorhersagen
CREATE OR REPLACE FUNCTION trigger_averages_refresh()
RETURNS TRIGGER AS $$
BEGIN
    -- Refresh nur wenn signifikante Änderungen
    IF (TG_OP = 'INSERT') OR 
       (TG_OP = 'UPDATE' AND OLD.status != NEW.status) THEN
        -- Asynchrone Aktualisierung (nicht blockierend)
        PERFORM pg_notify('refresh_averages', 'new_prediction');
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Trigger nur bei relevanten Änderungen
DROP TRIGGER IF EXISTS trigger_prediction_averages_refresh ON prediction_tracking_unified;
CREATE TRIGGER trigger_prediction_averages_refresh
    AFTER INSERT OR UPDATE OF status, actual_value ON prediction_tracking_unified
    FOR EACH ROW
    EXECUTE FUNCTION trigger_averages_refresh();

-- ===============================================================================
-- TEST DATA für Entwicklung/Testing
-- ===============================================================================

-- Initial Refresh der Materialized View
SELECT refresh_ki_prognosen_averages();

-- Verify Installation
SELECT 
    'Enhanced KI-Prognosen Averages GUI v1.0.0 erfolgreich installiert' as status,
    COUNT(*) as symbols_with_averages,
    STRING_AGG(DISTINCT horizon_type, ', ') as available_timeframes
FROM mv_ki_prognosen_averages;

-- Performance Test Query (sollte unter 100ms laufen)
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM get_ki_prognosen_with_averages('1M', 15);