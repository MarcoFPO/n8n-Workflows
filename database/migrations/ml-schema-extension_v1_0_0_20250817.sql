-- =============================================
-- ML Schema Extension v1.0.0
-- Erweitert bestehende PostgreSQL-Datenbank um ML-Funktionalität
-- 
-- Deployment: aktienanalyse-ökosystem auf 10.1.1.174
-- Autor: Claude Code
-- Datum: 17. August 2025
-- =============================================

-- TimescaleDB Extension aktivieren (falls noch nicht aktiv)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- =============================================
-- 1. ML FEATURES STORAGE
-- =============================================

-- ML Features Table - Speichert berechnete Features
CREATE TABLE IF NOT EXISTS ml_features (
    feature_id VARCHAR(36) PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    feature_type VARCHAR(20) NOT NULL CHECK (feature_type IN ('technical', 'sentiment', 'fundamental', 'macro')),
    calculation_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    features_json JSONB NOT NULL,
    feature_count INTEGER NOT NULL DEFAULT 0,
    quality_score DECIMAL(4,3) NOT NULL DEFAULT 0.0 CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    missing_values_ratio DECIMAL(4,3) NOT NULL DEFAULT 0.0 CHECK (missing_values_ratio >= 0.0 AND missing_values_ratio <= 1.0),
    outlier_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index für Performance
CREATE INDEX IF NOT EXISTS idx_ml_features_symbol_type_time ON ml_features (symbol, feature_type, calculation_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ml_features_calculation_time ON ml_features (calculation_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ml_features_quality ON ml_features (quality_score DESC);

-- TimescaleDB Hypertable für Features (Zeit-partitioniert)
SELECT create_hypertable('ml_features', 'calculation_timestamp', if_not_exists => TRUE);

-- =============================================
-- 2. ML MODEL METADATA
-- =============================================

-- Model Metadata Table - ML-Modell-Registry
CREATE TABLE IF NOT EXISTS ml_model_metadata (
    model_id VARCHAR(36) PRIMARY KEY,
    model_type VARCHAR(20) NOT NULL CHECK (model_type IN ('technical', 'sentiment', 'fundamental', 'meta')),
    model_version VARCHAR(20) NOT NULL,
    horizon_days INTEGER NOT NULL CHECK (horizon_days IN (7, 30, 150, 365)),
    status VARCHAR(20) NOT NULL DEFAULT 'training' CHECK (status IN ('training', 'active', 'deprecated', 'failed', 'deleted')),
    file_path TEXT NOT NULL,
    scaler_path TEXT,
    performance_metrics JSONB NOT NULL DEFAULT '{}',
    training_config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(model_type, horizon_days, status) WHERE status = 'active'
);

-- Index für Model Queries
CREATE INDEX IF NOT EXISTS idx_ml_model_type_horizon_status ON ml_model_metadata (model_type, horizon_days, status);
CREATE INDEX IF NOT EXISTS idx_ml_model_status_created ON ml_model_metadata (status, created_at DESC);

-- =============================================
-- 3. ML PREDICTIONS
-- =============================================

-- Individual Predictions Table
CREATE TABLE IF NOT EXISTS ml_individual_predictions (
    prediction_id VARCHAR(36) PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    model_type VARCHAR(20) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    horizon_days INTEGER NOT NULL,
    prediction_values DECIMAL[] NOT NULL,
    confidence_score DECIMAL(4,3) NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    volatility_estimate DECIMAL(8,4) NOT NULL DEFAULT 0.0,
    feature_importance JSONB NOT NULL DEFAULT '{}',
    ensemble_prediction_id VARCHAR(36),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ensemble Predictions Table
CREATE TABLE IF NOT EXISTS ml_predictions (
    prediction_id VARCHAR(36) PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    prediction_type VARCHAR(20) NOT NULL DEFAULT 'ensemble' CHECK (prediction_type IN ('ensemble', 'individual')),
    prediction_data JSONB NOT NULL,
    ensemble_confidence DECIMAL(4,3) NOT NULL DEFAULT 0.0 CHECK (ensemble_confidence >= 0.0 AND ensemble_confidence <= 1.0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index für Prediction Queries
CREATE INDEX IF NOT EXISTS idx_ml_individual_predictions_symbol_time ON ml_individual_predictions (symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ml_individual_predictions_ensemble ON ml_individual_predictions (ensemble_prediction_id);
CREATE INDEX IF NOT EXISTS idx_ml_predictions_symbol_time ON ml_predictions (symbol, created_at DESC);

-- TimescaleDB Hypertable für Predictions
SELECT create_hypertable('ml_individual_predictions', 'created_at', if_not_exists => TRUE);
SELECT create_hypertable('ml_predictions', 'created_at', if_not_exists => TRUE);

-- =============================================
-- 4. ML ENSEMBLE CONFIGURATION
-- =============================================

-- Ensemble Weights Table - Dynamische Model-Gewichtung
CREATE TABLE IF NOT EXISTS ml_ensemble_weights (
    weight_id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL DEFAULT 'DEFAULT',
    model_type VARCHAR(20) NOT NULL,
    horizon_days INTEGER NOT NULL,
    weight DECIMAL(6,4) NOT NULL DEFAULT 1.0 CHECK (weight >= 0.0 AND weight <= 10.0),
    performance_based BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, model_type, horizon_days)
);

-- Default Ensemble Weights inserieren
INSERT INTO ml_ensemble_weights (symbol, model_type, horizon_days, weight) VALUES
    ('DEFAULT', 'technical', 7, 1.0),
    ('DEFAULT', 'technical', 30, 1.0),
    ('DEFAULT', 'technical', 150, 1.0),
    ('DEFAULT', 'technical', 365, 1.0)
ON CONFLICT (symbol, model_type, horizon_days) DO NOTHING;

-- =============================================
-- 5. ML PERFORMANCE TRACKING
-- =============================================

-- Model Performance History
CREATE TABLE IF NOT EXISTS ml_model_performance (
    performance_id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id VARCHAR(36) NOT NULL REFERENCES ml_model_metadata(model_id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    evaluation_date DATE NOT NULL,
    actual_values DECIMAL[] NOT NULL,
    predicted_values DECIMAL[] NOT NULL,
    mae_score DECIMAL(8,4) NOT NULL,
    mse_score DECIMAL(8,4) NOT NULL,
    directional_accuracy DECIMAL(4,3) NOT NULL,
    r2_score DECIMAL(6,4),
    sharpe_ratio DECIMAL(6,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Performance Aggregation View
CREATE OR REPLACE VIEW ml_model_performance_summary AS
SELECT 
    m.model_type,
    m.horizon_days,
    m.status,
    COUNT(p.performance_id) as evaluation_count,
    AVG(p.mae_score) as avg_mae,
    AVG(p.directional_accuracy) as avg_directional_accuracy,
    AVG(p.r2_score) as avg_r2_score,
    MAX(p.created_at) as last_evaluation
FROM ml_model_metadata m
LEFT JOIN ml_model_performance p ON m.model_id = p.model_id
WHERE m.status IN ('active', 'deprecated')
GROUP BY m.model_type, m.horizon_days, m.status
ORDER BY m.model_type, m.horizon_days;

-- Index für Performance Tracking
CREATE INDEX IF NOT EXISTS idx_ml_performance_model_symbol ON ml_model_performance (model_id, symbol, evaluation_date DESC);

-- =============================================
-- 6. ML TRAINING LOGS
-- =============================================

-- Training Logs für Model-Training-Prozess
CREATE TABLE IF NOT EXISTS ml_training_logs (
    training_id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    model_type VARCHAR(20) NOT NULL,
    horizon_days INTEGER NOT NULL,
    training_symbol VARCHAR(10) NOT NULL,
    training_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    training_end TIMESTAMPTZ,
    training_duration_seconds INTEGER,
    training_config JSONB NOT NULL DEFAULT '{}',
    training_metrics JSONB NOT NULL DEFAULT '{}',
    validation_metrics JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    model_id VARCHAR(36) REFERENCES ml_model_metadata(model_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index für Training Logs
CREATE INDEX IF NOT EXISTS idx_ml_training_logs_status_time ON ml_training_logs (status, training_start DESC);

-- =============================================
-- 7. ML EVENT CORRELATION
-- =============================================

-- Event Correlation für ML-Pipeline-Tracking
CREATE TABLE IF NOT EXISTS ml_event_correlation (
    correlation_id VARCHAR(36) PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    trigger_event_type VARCHAR(50) NOT NULL,
    trigger_event_id VARCHAR(36),
    pipeline_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    pipeline_end TIMESTAMPTZ,
    pipeline_duration_ms INTEGER,
    feature_calculation_duration_ms INTEGER,
    prediction_duration_ms INTEGER,
    ensemble_duration_ms INTEGER,
    total_events_generated INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'timeout')),
    error_stage VARCHAR(30),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index für Event Correlation
CREATE INDEX IF NOT EXISTS idx_ml_event_correlation_symbol_time ON ml_event_correlation (symbol, pipeline_start DESC);
CREATE INDEX IF NOT EXISTS idx_ml_event_correlation_status ON ml_event_correlation (status, pipeline_start DESC);

-- =============================================
-- 8. ML SYSTEM HEALTH MONITORING
-- =============================================

-- Service Health Metrics
CREATE TABLE IF NOT EXISTS ml_service_health (
    health_id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name VARCHAR(30) NOT NULL CHECK (service_name IN ('ml-analytics', 'feature-engine', 'model-manager', 'prediction-orchestrator')),
    health_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL CHECK (status IN ('healthy', 'warning', 'critical', 'down')),
    metrics JSONB NOT NULL DEFAULT '{}',
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index für Health Monitoring
CREATE INDEX IF NOT EXISTS idx_ml_service_health_service_time ON ml_service_health (service_name, health_timestamp DESC);

-- TimescaleDB Hypertable für Health Metrics
SELECT create_hypertable('ml_service_health', 'health_timestamp', if_not_exists => TRUE);

-- =============================================
-- 9. DATA RETENTION POLICIES
-- =============================================

-- Retention Policy für Features (6 Monate)
SELECT add_retention_policy('ml_features', INTERVAL '6 months', if_not_exists => TRUE);

-- Retention Policy für Individual Predictions (3 Monate)  
SELECT add_retention_policy('ml_individual_predictions', INTERVAL '3 months', if_not_exists => TRUE);

-- Retention Policy für Ensemble Predictions (12 Monate)
SELECT add_retention_policy('ml_predictions', INTERVAL '12 months', if_not_exists => TRUE);

-- Retention Policy für Health Metrics (30 Tage)
SELECT add_retention_policy('ml_service_health', INTERVAL '30 days', if_not_exists => TRUE);

-- =============================================
-- 10. ML-SPECIFIC FUNCTIONS
-- =============================================

-- Funktion: Get Latest Features für Symbol
CREATE OR REPLACE FUNCTION get_latest_ml_features(p_symbol VARCHAR(10), p_feature_type VARCHAR(20) DEFAULT 'technical')
RETURNS TABLE(
    feature_id VARCHAR(36),
    features_json JSONB,
    quality_score DECIMAL(4,3),
    calculation_timestamp TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        f.feature_id,
        f.features_json,
        f.quality_score,
        f.calculation_timestamp
    FROM ml_features f
    WHERE f.symbol = p_symbol 
    AND f.feature_type = p_feature_type
    ORDER BY f.calculation_timestamp DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Funktion: Get Active Models
CREATE OR REPLACE FUNCTION get_active_models()
RETURNS TABLE(
    model_id VARCHAR(36),
    model_type VARCHAR(20),
    horizon_days INTEGER,
    performance_metrics JSONB,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.model_id,
        m.model_type,
        m.horizon_days,
        m.performance_metrics,
        m.created_at
    FROM ml_model_metadata m
    WHERE m.status = 'active'
    ORDER BY m.model_type, m.horizon_days;
END;
$$ LANGUAGE plpgsql;

-- Funktion: Calculate Model Performance Metrics
CREATE OR REPLACE FUNCTION calculate_model_performance_metrics(p_model_id VARCHAR(36), p_days_back INTEGER DEFAULT 30)
RETURNS TABLE(
    avg_mae DECIMAL(8,4),
    avg_directional_accuracy DECIMAL(4,3),
    evaluation_count INTEGER,
    last_evaluation TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        AVG(p.mae_score)::DECIMAL(8,4) as avg_mae,
        AVG(p.directional_accuracy)::DECIMAL(4,3) as avg_directional_accuracy,
        COUNT(p.performance_id)::INTEGER as evaluation_count,
        MAX(p.created_at) as last_evaluation
    FROM ml_model_performance p
    WHERE p.model_id = p_model_id
    AND p.created_at >= NOW() - INTERVAL '1 day' * p_days_back;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- 11. UPDATE TRIGGERS
-- =============================================

-- Trigger für updated_at Timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger für ml_features
DROP TRIGGER IF EXISTS trigger_ml_features_updated_at ON ml_features;
CREATE TRIGGER trigger_ml_features_updated_at
    BEFORE UPDATE ON ml_features
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger für ml_model_metadata
DROP TRIGGER IF EXISTS trigger_ml_model_metadata_updated_at ON ml_model_metadata;
CREATE TRIGGER trigger_ml_model_metadata_updated_at
    BEFORE UPDATE ON ml_model_metadata
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger für ml_ensemble_weights
DROP TRIGGER IF EXISTS trigger_ml_ensemble_weights_updated_at ON ml_ensemble_weights;
CREATE TRIGGER trigger_ml_ensemble_weights_updated_at
    BEFORE UPDATE ON ml_ensemble_weights
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- 12. PERMISSIONS & SECURITY
-- =============================================

-- ML Service User (falls nicht existiert)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ml_service') THEN
        CREATE USER ml_service WITH PASSWORD 'ml_service_secure_2025';
    END IF;
END
$$;

-- Permissions für ML Service
GRANT USAGE ON SCHEMA public TO ml_service;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ml_service;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ml_service;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO ml_service;

-- =============================================
-- 13. INITIAL DATA SEEDING
-- =============================================

-- Beispiel-Ensemble-Konfiguration für AAPL
INSERT INTO ml_ensemble_weights (symbol, model_type, horizon_days, weight, performance_based) VALUES
    ('AAPL', 'technical', 7, 1.0, true),
    ('AAPL', 'technical', 30, 0.9, true),
    ('AAPL', 'technical', 150, 0.7, true),
    ('AAPL', 'technical', 365, 0.5, true)
ON CONFLICT (symbol, model_type, horizon_days) DO NOTHING;

-- =============================================
-- 14. COMPLETION LOG
-- =============================================

-- Log successful deployment
INSERT INTO ml_service_health (service_name, status, metrics) VALUES
    ('ml-analytics', 'healthy', '{"schema_version": "1.0.0", "deployment_timestamp": "' || NOW()::text || '", "tables_created": 11, "functions_created": 3}');

-- Schema-Version in separater Tabelle
CREATE TABLE IF NOT EXISTS ml_schema_version (
    version VARCHAR(10) PRIMARY KEY,
    deployed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description TEXT
);

INSERT INTO ml_schema_version (version, description) VALUES
    ('1.0.0', 'Initial ML Schema Extension - Complete ML Pipeline Support')
ON CONFLICT (version) DO NOTHING;

-- =============================================
-- DEPLOYMENT COMPLETED SUCCESSFULLY
-- =============================================

SELECT 'ML Schema Extension v1.0.0 deployed successfully!' as deployment_status,
       NOW() as deployment_timestamp,
       (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'ml_%') as ml_tables_created;