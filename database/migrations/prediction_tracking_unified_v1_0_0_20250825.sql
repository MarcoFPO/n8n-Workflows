-- ===============================================================================
-- Unified Prediction Tracking Schema v1.0.0
-- Vollständiges SOLL-IST Tracking mit korrekten Zeitstempeln
-- 
-- CLEAN ARCHITECTURE PRINCIPLE:
-- - Single Responsibility: Nur Prediction Tracking
-- - Data Integrity: Vollständige Zeitstempel-Erfassung
-- 
-- Anforderungen:
-- a) Tag der Berechnung (calculation_date)
-- b) Zeitpunkt für Eintritt der Vorhersage (target_date)
-- c) IST-Gewinn zum Zeitpunkt des Eintritts (actual_value mit evaluation_date)
--
-- Autor: Claude Code
-- Datum: 25. August 2025
-- Version: 1.0.0
-- ===============================================================================

-- Drop existing tables for clean setup
DROP TABLE IF EXISTS prediction_tracking_unified CASCADE;
DROP TABLE IF EXISTS prediction_evaluation_queue CASCADE;
DROP TABLE IF EXISTS prediction_performance_metrics CASCADE;

-- ===============================================================================
-- HAUPTTABELLE: Unified Prediction Tracking
-- ===============================================================================
CREATE TABLE prediction_tracking_unified (
    id SERIAL PRIMARY KEY,
    
    -- Identifikation
    prediction_id UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    company_name VARCHAR(255),
    
    -- ZEITSTEMPEL (3 Pflicht-Anforderungen)
    calculation_date TIMESTAMP WITH TIME ZONE NOT NULL,  -- a) Wann wurde berechnet
    target_date DATE NOT NULL,                          -- b) Für wann gilt die Vorhersage
    evaluation_date TIMESTAMP WITH TIME ZONE,           -- c) Wann wurde IST erfasst
    
    -- WERTE
    predicted_value DECIMAL(12,4) NOT NULL,             -- SOLL-Wert (Gewinn-Vorhersage)
    actual_value DECIMAL(12,4),                         -- IST-Wert (tatsächlicher Gewinn)
    performance_diff DECIMAL(12,4) GENERATED ALWAYS AS  -- Automatische Differenz
        (actual_value - predicted_value) STORED,
    performance_accuracy DECIMAL(5,2) GENERATED ALWAYS AS -- Genauigkeit in %
        (CASE 
            WHEN predicted_value = 0 THEN NULL
            WHEN actual_value IS NULL THEN NULL
            ELSE (1 - ABS(actual_value - predicted_value) / ABS(predicted_value)) * 100
        END) STORED,
    
    -- Horizont-Information
    horizon_type VARCHAR(10) NOT NULL CHECK (horizon_type IN ('1W', '1M', '3M', '12M')),
    horizon_days INTEGER NOT NULL,
    
    -- Metadaten
    confidence_score DECIMAL(5,4) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    model_version VARCHAR(50),
    model_type VARCHAR(50),
    calculation_method VARCHAR(50) DEFAULT 'ensemble',
    
    -- Tracking Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'evaluated', 'expired', 'error')),
    evaluation_attempts INTEGER DEFAULT 0,
    last_evaluation_attempt TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_prediction UNIQUE(symbol, calculation_date, target_date, horizon_type),
    CONSTRAINT valid_dates CHECK (target_date >= calculation_date::date),
    CONSTRAINT valid_horizon CHECK (horizon_days > 0)
);

-- Performance Indexes
CREATE INDEX idx_tracking_symbol_dates ON prediction_tracking_unified(symbol, target_date, calculation_date);
CREATE INDEX idx_tracking_evaluation_pending ON prediction_tracking_unified(target_date, status) 
    WHERE status = 'pending';
CREATE INDEX idx_tracking_target_date ON prediction_tracking_unified(target_date);
CREATE INDEX idx_tracking_calculation_date ON prediction_tracking_unified(calculation_date);
CREATE INDEX idx_tracking_status ON prediction_tracking_unified(status);
CREATE INDEX idx_tracking_symbol_horizon ON prediction_tracking_unified(symbol, horizon_type);

-- ===============================================================================
-- EVALUATION QUEUE: Für automatische IST-Berechnung
-- ===============================================================================
CREATE TABLE prediction_evaluation_queue (
    id SERIAL PRIMARY KEY,
    prediction_id UUID REFERENCES prediction_tracking_unified(prediction_id) ON DELETE CASCADE,
    target_date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    
    -- Processing Status
    processing_status VARCHAR(20) DEFAULT 'pending' 
        CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'retry')),
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Error Tracking
    last_error TEXT,
    last_error_at TIMESTAMP WITH TIME ZONE,
    
    -- Scheduling
    scheduled_for TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_queue_entry UNIQUE(prediction_id)
);

-- Queue Indexes
CREATE INDEX idx_queue_pending ON prediction_evaluation_queue(scheduled_for, processing_status) 
    WHERE processing_status IN ('pending', 'retry');
CREATE INDEX idx_queue_target_date ON prediction_evaluation_queue(target_date);
CREATE INDEX idx_queue_status ON prediction_evaluation_queue(processing_status);

-- ===============================================================================
-- PERFORMANCE METRICS: Aggregierte Metriken
-- ===============================================================================
CREATE TABLE prediction_performance_metrics (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    horizon_type VARCHAR(10) NOT NULL,
    metric_date DATE NOT NULL,
    
    -- Aggregierte Metriken
    total_predictions INTEGER DEFAULT 0,
    evaluated_predictions INTEGER DEFAULT 0,
    pending_predictions INTEGER DEFAULT 0,
    
    -- Performance Metriken
    avg_accuracy DECIMAL(5,2),
    avg_absolute_error DECIMAL(12,4),
    directional_accuracy DECIMAL(5,2), -- % der korrekten Richtungs-Vorhersagen
    
    -- Beste/Schlechteste Performance
    best_prediction_id UUID,
    best_accuracy DECIMAL(5,2),
    worst_prediction_id UUID,
    worst_accuracy DECIMAL(5,2),
    
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_metrics UNIQUE(symbol, horizon_type, metric_date)
);

-- Metrics Indexes
CREATE INDEX idx_metrics_symbol_date ON prediction_performance_metrics(symbol, metric_date DESC);
CREATE INDEX idx_metrics_horizon ON prediction_performance_metrics(horizon_type, metric_date DESC);

-- ===============================================================================
-- STORED PROCEDURES
-- ===============================================================================

-- Funktion zum Hinzufügen einer neuen Vorhersage
CREATE OR REPLACE FUNCTION add_prediction(
    p_symbol VARCHAR(10),
    p_company_name VARCHAR(255),
    p_predicted_value DECIMAL(12,4),
    p_horizon_type VARCHAR(10),
    p_horizon_days INTEGER,
    p_confidence_score DECIMAL(5,4) DEFAULT NULL,
    p_model_version VARCHAR(50) DEFAULT NULL,
    p_model_type VARCHAR(50) DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_prediction_id UUID;
    v_target_date DATE;
BEGIN
    -- Berechne target_date basierend auf horizon_days
    v_target_date := CURRENT_DATE + (p_horizon_days || ' days')::INTERVAL;
    
    -- Füge Vorhersage ein
    INSERT INTO prediction_tracking_unified (
        symbol, company_name, 
        calculation_date, target_date,
        predicted_value, 
        horizon_type, horizon_days,
        confidence_score, model_version, model_type
    ) VALUES (
        p_symbol, p_company_name,
        CURRENT_TIMESTAMP, v_target_date,
        p_predicted_value,
        p_horizon_type, p_horizon_days,
        p_confidence_score, p_model_version, p_model_type
    ) RETURNING prediction_id INTO v_prediction_id;
    
    -- Füge zur Evaluation Queue hinzu
    INSERT INTO prediction_evaluation_queue (
        prediction_id, target_date, symbol, scheduled_for
    ) VALUES (
        v_prediction_id, v_target_date, p_symbol, v_target_date::timestamp
    );
    
    RETURN v_prediction_id;
END;
$$ LANGUAGE plpgsql;

-- Funktion zum Evaluieren einer Vorhersage (IST-Wert setzen)
CREATE OR REPLACE FUNCTION evaluate_prediction(
    p_prediction_id UUID,
    p_actual_value DECIMAL(12,4)
)
RETURNS BOOLEAN AS $$
BEGIN
    -- Update Haupttabelle
    UPDATE prediction_tracking_unified
    SET 
        actual_value = p_actual_value,
        evaluation_date = CURRENT_TIMESTAMP,
        status = 'evaluated',
        updated_at = CURRENT_TIMESTAMP
    WHERE prediction_id = p_prediction_id
    AND status = 'pending';
    
    -- Update Queue
    UPDATE prediction_evaluation_queue
    SET 
        processing_status = 'completed',
        processing_completed_at = CURRENT_TIMESTAMP
    WHERE prediction_id = p_prediction_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Funktion zum Abrufen fälliger Evaluierungen
CREATE OR REPLACE FUNCTION get_pending_evaluations(
    p_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    prediction_id UUID,
    symbol VARCHAR(10),
    company_name VARCHAR(255),
    predicted_value DECIMAL(12,4),
    target_date DATE,
    horizon_type VARCHAR(10),
    calculation_date TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pt.prediction_id,
        pt.symbol,
        pt.company_name,
        pt.predicted_value,
        pt.target_date,
        pt.horizon_type,
        pt.calculation_date
    FROM prediction_tracking_unified pt
    INNER JOIN prediction_evaluation_queue eq ON pt.prediction_id = eq.prediction_id
    WHERE pt.target_date <= p_date
    AND pt.status = 'pending'
    AND eq.processing_status IN ('pending', 'retry')
    AND eq.retry_count < eq.max_retries
    ORDER BY pt.target_date, eq.priority DESC;
END;
$$ LANGUAGE plpgsql;

-- ===============================================================================
-- TRIGGER für updated_at
-- ===============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_prediction_tracking_updated_at
    BEFORE UPDATE ON prediction_tracking_unified
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===============================================================================
-- VIEWS für Reporting
-- ===============================================================================

-- View für SOLL-IST Vergleich
CREATE OR REPLACE VIEW v_soll_ist_comparison AS
SELECT 
    symbol,
    company_name,
    horizon_type,
    calculation_date::date as berechnung_datum,
    target_date as vorhersage_datum,
    evaluation_date::date as bewertung_datum,
    predicted_value as soll_gewinn,
    actual_value as ist_gewinn,
    performance_diff as differenz,
    performance_accuracy as genauigkeit_prozent,
    confidence_score,
    status,
    CASE 
        WHEN actual_value IS NOT NULL AND predicted_value > 0 AND actual_value > 0 THEN 'RICHTIG_POSITIV'
        WHEN actual_value IS NOT NULL AND predicted_value < 0 AND actual_value < 0 THEN 'RICHTIG_NEGATIV'
        WHEN actual_value IS NOT NULL AND predicted_value > 0 AND actual_value <= 0 THEN 'FALSCH_POSITIV'
        WHEN actual_value IS NOT NULL AND predicted_value < 0 AND actual_value >= 0 THEN 'FALSCH_NEGATIV'
        ELSE 'AUSSTEHEND'
    END as richtungs_bewertung
FROM prediction_tracking_unified
ORDER BY target_date DESC, symbol;

-- View für Performance-Übersicht nach Symbol und Horizont
CREATE OR REPLACE VIEW v_performance_summary AS
SELECT 
    symbol,
    horizon_type,
    COUNT(*) as total_vorhersagen,
    COUNT(CASE WHEN status = 'evaluated' THEN 1 END) as bewertete_vorhersagen,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as ausstehende_vorhersagen,
    AVG(CASE WHEN status = 'evaluated' THEN performance_accuracy END) as durchschnitt_genauigkeit,
    AVG(CASE WHEN status = 'evaluated' THEN ABS(performance_diff) END) as durchschnitt_absoluter_fehler,
    SUM(CASE 
        WHEN status = 'evaluated' AND 
             SIGN(predicted_value) = SIGN(actual_value) THEN 1 
        ELSE 0 
    END)::DECIMAL / NULLIF(COUNT(CASE WHEN status = 'evaluated' THEN 1 END), 0) * 100 as richtungs_genauigkeit,
    MIN(calculation_date) as erste_vorhersage,
    MAX(calculation_date) as letzte_vorhersage
FROM prediction_tracking_unified
GROUP BY symbol, horizon_type
ORDER BY symbol, horizon_type;

-- View für tägliche Evaluation-Aufgaben
CREATE OR REPLACE VIEW v_daily_evaluation_tasks AS
SELECT 
    target_date,
    COUNT(*) as anzahl_faellig,
    STRING_AGG(DISTINCT symbol, ', ' ORDER BY symbol) as betroffene_symbole,
    MIN(calculation_date) as aelteste_vorhersage,
    MAX(calculation_date) as neueste_vorhersage
FROM prediction_tracking_unified
WHERE status = 'pending'
AND target_date <= CURRENT_DATE
GROUP BY target_date
ORDER BY target_date;

-- ===============================================================================
-- INITIAL DATA für Testing
-- ===============================================================================
-- Beispiel-Vorhersagen für verschiedene Horizonte
DO $$
DECLARE
    v_symbols TEXT[] := ARRAY['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'];
    v_horizons TEXT[] := ARRAY['1W', '1M', '3M', '12M'];
    v_horizon_days INTEGER[] := ARRAY[7, 30, 90, 365];
    v_symbol TEXT;
    v_horizon TEXT;
    v_days INTEGER;
    i INTEGER;
BEGIN
    FOREACH v_symbol IN ARRAY v_symbols LOOP
        FOR i IN 1..array_length(v_horizons, 1) LOOP
            v_horizon := v_horizons[i];
            v_days := v_horizon_days[i];
            
            -- Füge Test-Vorhersage hinzu
            PERFORM add_prediction(
                v_symbol,
                v_symbol || ' Inc.',
                (random() * 20 - 5)::DECIMAL(12,4), -- -5% bis +15% Vorhersage
                v_horizon,
                v_days,
                (0.7 + random() * 0.25)::DECIMAL(5,4), -- 70-95% Confidence
                'v6.1.0',
                'ensemble'
            );
        END LOOP;
    END LOOP;
END $$;

-- Success Message
SELECT 'Unified Prediction Tracking Schema v1.0.0 erfolgreich erstellt' as status,
       COUNT(*) as test_predictions_created 
FROM prediction_tracking_unified;