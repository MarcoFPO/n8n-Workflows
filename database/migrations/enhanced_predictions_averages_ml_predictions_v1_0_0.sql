-- ===============================================================================
-- Enhanced Predictions Averages für ml_predictions Tabelle v1.0.0
-- Durchschnittswerte-Integration für KI-Prognosen GUI
-- 
-- CLEAN ARCHITECTURE PRINCIPLE:
-- - Single Responsibility: Durchschnittswerte-Erweiterung für bestehende ml_predictions
-- - Open/Closed: Erweiterung ohne Änderung bestehender Funktionalität
-- - Performance-optimiert: Materialized Views für <2s Ladezeit
--
-- Ziel: Durchschnittswerte in KI-Prognosen GUI anzeigen
-- Basistabelle: ml_predictions (existiert bereits)
-- 
-- Autor: Claude Code
-- Datum: 26. August 2025
-- Version: 1.0.0
-- ===============================================================================

BEGIN;

-- ===============================================================================
-- STEP 1: ERWEITERTE VIEWS FÜR DURCHSCHNITTSWERTE-BERECHNUNG
-- ===============================================================================

-- View für Durchschnittswerte-Extraktion aus JSONB prediction_data
CREATE OR REPLACE VIEW v_ml_predictions_enhanced AS
SELECT 
    prediction_id,
    symbol,
    prediction_type,
    ensemble_confidence,
    created_at,
    
    -- JSONB-Extraction für Vorhersagewerte
    COALESCE((prediction_data->>'predicted_value')::numeric, 0) as predicted_value,
    COALESCE((prediction_data->>'target_price')::numeric, 0) as target_price,
    COALESCE((prediction_data->>'horizon_days')::integer, 30) as horizon_days,
    
    -- Zeitrahmen-Klassifizierung
    CASE 
        WHEN COALESCE((prediction_data->>'horizon_days')::integer, 30) <= 7 THEN '1W'
        WHEN COALESCE((prediction_data->>'horizon_days')::integer, 30) <= 30 THEN '1M'
        WHEN COALESCE((prediction_data->>'horizon_days')::integer, 30) <= 90 THEN '3M'
        ELSE '12M'
    END as timeframe,
    
    -- Zusätzliche Metadaten aus JSONB
    prediction_data->>'model_name' as model_name,
    COALESCE((prediction_data->>'confidence')::numeric, ensemble_confidence) as model_confidence
    
FROM ml_predictions
WHERE prediction_data IS NOT NULL;

-- ===============================================================================
-- STEP 2: DURCHSCHNITTSWERTE MATERIALIZED VIEW
-- ===============================================================================

-- Materialized View für Performance-optimierte Durchschnittswerte-Abfragen
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_ki_prognosen_averages AS
SELECT 
    symbol,
    timeframe,
    horizon_days,
    
    -- Durchschnittswerte-Berechnung (Kernfunktionalität für GUI)
    COUNT(*) as prediction_count,
    AVG(predicted_value) as avg_predicted_value,
    AVG(target_price) as avg_target_price,
    AVG(model_confidence) as avg_confidence,
    
    -- Abweichungs-Statistiken für Performance-Indikator
    STDDEV(predicted_value) as predicted_value_stddev,
    MIN(predicted_value) as min_predicted_value,
    MAX(predicted_value) as max_predicted_value,
    
    -- Zeitbereich für Timeline-Navigation
    MIN(created_at) as earliest_prediction,
    MAX(created_at) as latest_prediction,
    
    -- Aktualisierungs-Metadaten
    NOW() as last_updated
    
FROM v_ml_predictions_enhanced
GROUP BY symbol, timeframe, horizon_days
HAVING COUNT(*) >= 2;  -- Mindestens 2 Predictions für sinnvolle Durchschnitte

-- Index für Performance-optimierte Symbol-Lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_ki_prognosen_averages_symbol_timeframe 
ON mv_ki_prognosen_averages(symbol, timeframe);

-- ===============================================================================
-- STEP 3: KI-PROGNOSEN GUI-KOMPATIBLE VIEW
-- ===============================================================================

-- View für GUI mit Durchschnittswerten und Abweichungen
CREATE OR REPLACE VIEW v_ki_prognosen_with_averages AS
SELECT 
    p.prediction_id,
    p.symbol,
    p.prediction_type,
    p.created_at::date as calculation_date,
    p.predicted_value,
    p.target_price,
    p.model_confidence as confidence_score,
    p.timeframe,
    p.horizon_days,
    
    -- Durchschnittswerte aus Materialized View
    COALESCE(avg.avg_predicted_value, p.predicted_value) as avg_prediction,
    COALESCE(avg.avg_confidence, p.model_confidence) as avg_confidence,
    
    -- Abweichung vom Durchschnitt (für GUI-Darstellung)
    CASE 
        WHEN avg.avg_predicted_value IS NOT NULL THEN
            ROUND(((p.predicted_value - avg.avg_predicted_value) / avg.avg_predicted_value * 100)::numeric, 2)
        ELSE 0
    END as deviation_percent,
    
    -- Performance-Indikator basierend auf Standardabweichung
    CASE 
        WHEN avg.predicted_value_stddev IS NULL OR avg.predicted_value_stddev = 0 THEN 'STABLE'
        WHEN ABS(p.predicted_value - avg.avg_predicted_value) <= avg.predicted_value_stddev THEN 'NORMAL'
        WHEN p.predicted_value > avg.avg_predicted_value + avg.predicted_value_stddev THEN 'HIGH_VOLATILITY'
        ELSE 'LOW_VOLATILITY'
    END as performance_indicator,
    
    -- Datenbasis für GUI-Anzeige
    COALESCE(avg.prediction_count, 1) as data_basis_count,
    avg.last_updated as avg_calculation_date
    
FROM v_ml_predictions_enhanced p
LEFT JOIN mv_ki_prognosen_averages avg 
    ON p.symbol = avg.symbol AND p.timeframe = avg.timeframe
ORDER BY p.created_at DESC, p.symbol;

-- ===============================================================================
-- STEP 4: STORED FUNCTION FÜR DURCHSCHNITTSWERTE-ABRUF
-- ===============================================================================

-- Function für Timeline-kompatible Durchschnittswerte-Abfrage
CREATE OR REPLACE FUNCTION get_ki_prognosen_with_averages(
    p_timeframe TEXT DEFAULT '1M',
    p_limit INTEGER DEFAULT 50,
    p_symbol TEXT DEFAULT NULL
)
RETURNS TABLE (
    symbol TEXT,
    calculation_date DATE,
    predicted_value NUMERIC,
    avg_prediction NUMERIC,
    deviation_percent NUMERIC,
    avg_confidence NUMERIC,
    performance_indicator TEXT,
    data_basis_count BIGINT
) 
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.symbol::TEXT,
        v.calculation_date,
        v.predicted_value::NUMERIC,
        v.avg_prediction::NUMERIC,
        v.deviation_percent::NUMERIC,
        v.avg_confidence::NUMERIC,
        v.performance_indicator::TEXT,
        v.data_basis_count
    FROM v_ki_prognosen_with_averages v
    WHERE 
        (p_timeframe IS NULL OR v.timeframe = p_timeframe)
        AND (p_symbol IS NULL OR v.symbol = p_symbol)
    ORDER BY v.calculation_date DESC, v.symbol
    LIMIT p_limit;
END;
$$;

-- ===============================================================================
-- STEP 5: MAINTENANCE FUNCTIONS
-- ===============================================================================

-- Function zum Refresh der Materialized View (Performance-Optimierung)
CREATE OR REPLACE FUNCTION refresh_ki_prognosen_averages_mv()
RETURNS BOOLEAN
LANGUAGE plpgsql AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_ki_prognosen_averages;
    
    -- Log refresh in system (optional)
    RAISE NOTICE 'Materialized View mv_ki_prognosen_averages erfolgreich aktualisiert um %', NOW();
    
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Fehler beim Refresh der Materialized View: %', SQLERRM;
        RETURN FALSE;
END;
$$;

-- Function für Cleanup alter Einträge (Disk Space Management)
CREATE OR REPLACE FUNCTION cleanup_old_ml_predictions(days_to_keep INTEGER DEFAULT 365)
RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM ml_predictions 
    WHERE created_at < (NOW() - (days_to_keep || ' days')::INTERVAL);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Materialized View nach Cleanup refreshen
    PERFORM refresh_ki_prognosen_averages_mv();
    
    RETURN deleted_count;
END;
$$;

-- ===============================================================================
-- STEP 6: PERFORMANCE-OPTIMIERTE INDIZES
-- ===============================================================================

-- Index für schnelle Symbol-Zeitrahmen-Lookups
CREATE INDEX IF NOT EXISTS idx_ml_predictions_symbol_created_timeframe 
ON ml_predictions(symbol, created_at DESC) 
WHERE prediction_data IS NOT NULL;

-- Partial Index für bessere Performance bei GUI-Abfragen
CREATE INDEX IF NOT EXISTS idx_ml_predictions_jsonb_predicted_value 
ON ml_predictions USING GIN (prediction_data) 
WHERE (prediction_data->>'predicted_value') IS NOT NULL;

-- ===============================================================================
-- STEP 7: INITIAL DATA POPULATION
-- ===============================================================================

-- Materialized View initial befüllen
SELECT refresh_ki_prognosen_averages_mv();

-- ===============================================================================
-- STEP 8: PERMISSIONS & SECURITY
-- ===============================================================================

-- Rechte für bestehende User vergeben (aktienanalyse)
GRANT SELECT ON v_ml_predictions_enhanced TO aktienanalyse;
GRANT SELECT ON mv_ki_prognosen_averages TO aktienanalyse;
GRANT SELECT ON v_ki_prognosen_with_averages TO aktienanalyse;
GRANT EXECUTE ON FUNCTION get_ki_prognosen_with_averages(TEXT, INTEGER, TEXT) TO aktienanalyse;
GRANT EXECUTE ON FUNCTION refresh_ki_prognosen_averages_mv() TO aktienanalyse;

-- ===============================================================================
-- MIGRATION VALIDATION
-- ===============================================================================

-- Test der neuen Funktionalität
DO $$
DECLARE
    test_count INTEGER;
    test_function_result INTEGER;
BEGIN
    -- Test 1: Views existieren und sind abfragbar
    SELECT COUNT(*) INTO test_count FROM v_ml_predictions_enhanced LIMIT 1;
    RAISE NOTICE 'Test 1 - Enhanced View: OK (% records accessible)', test_count;
    
    -- Test 2: Materialized View ist verfügbar
    SELECT COUNT(*) INTO test_count FROM mv_ki_prognosen_averages;
    RAISE NOTICE 'Test 2 - Materialized View: OK (% symbols with averages)', test_count;
    
    -- Test 3: GUI View funktioniert
    SELECT COUNT(*) INTO test_count FROM v_ki_prognosen_with_averages LIMIT 1;
    RAISE NOTICE 'Test 3 - GUI View: OK (% records available)', test_count;
    
    -- Test 4: Function ist aufrufbar
    SELECT COUNT(*) INTO test_function_result FROM get_ki_prognosen_with_averages('1M', 10);
    RAISE NOTICE 'Test 4 - Function Call: OK (% results returned)', test_function_result;
    
    RAISE NOTICE '✅ Migration erfolgreich abgeschlossen - Enhanced Predictions Averages bereit für GUI';
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION '❌ Migration Validation fehlgeschlagen: %', SQLERRM;
END;
$$;

COMMIT;

-- ===============================================================================
-- DEPLOYMENT SUCCESS CONFIRMATION
-- ===============================================================================

SELECT 
    'Enhanced Predictions Averages Migration v1.0.0 - ERFOLGREICH DEPLOYED' as status,
    NOW() as deployment_time,
    (SELECT COUNT(*) FROM mv_ki_prognosen_averages) as symbols_with_averages,
    (SELECT COUNT(DISTINCT symbol) FROM v_ml_predictions_enhanced) as total_symbols;