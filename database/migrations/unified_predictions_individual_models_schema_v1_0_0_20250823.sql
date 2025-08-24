-- Unified Predictions Individual Models Schema Extension v1.0.0
-- Erweitert unified_predictions Tabelle für strukturierte 4-Modell-Speicherung
-- 
-- CLEAN ARCHITECTURE PRINCIPLE: 
-- - Single Responsibility: Nur Datenbank-Schema für individuelle Modell-Vorhersagen
-- - Data Integrity: Structured JSON Schema mit Validierung
-- 
-- Autor: Claude Code
-- Datum: 23. August 2025
-- Version: 1.0.0

-- Drop existing table if exists for clean migration
DROP TABLE IF EXISTS unified_predictions_individual;

-- Create enhanced unified_predictions table with individual model support
CREATE TABLE unified_predictions_individual (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id TEXT UNIQUE NOT NULL,
    ensemble_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    company_name TEXT NOT NULL,
    
    -- SOLL Values (Final Ensemble Prediction)
    profit_forecast REAL NOT NULL,
    confidence_level REAL NOT NULL,
    forecast_period_days INTEGER NOT NULL,
    recommendation TEXT NOT NULL,
    trend TEXT NOT NULL,
    target_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    
    -- Source Management
    source_count INTEGER DEFAULT 4, -- 4 individual models
    source_reliability REAL DEFAULT 0.8,
    calculation_method TEXT DEFAULT 'ensemble',
    primary_source TEXT DEFAULT 'ml-analytics',
    
    -- Risk Assessment  
    risk_assessment TEXT DEFAULT 'medium',
    score REAL DEFAULT 0.5,
    
    -- IST Values (Actual Performance) - für spätere SOLL-IST Analyse
    actual_profit REAL DEFAULT NULL,
    actual_profit_calculated_at TEXT DEFAULT NULL,
    performance_difference REAL DEFAULT NULL,
    performance_accuracy REAL DEFAULT NULL,
    market_data_source TEXT DEFAULT NULL,
    
    -- INDIVIDUAL MODEL PREDICTIONS (Structured JSON)
    individual_technical_prediction TEXT DEFAULT NULL, -- JSON: technical model prediction
    individual_sentiment_prediction TEXT DEFAULT NULL, -- JSON: sentiment model prediction  
    individual_fundamental_prediction TEXT DEFAULT NULL, -- JSON: fundamental model prediction
    individual_meta_prediction TEXT DEFAULT NULL, -- JSON: meta model prediction
    
    -- ENSEMBLE METADATA
    ensemble_weights TEXT DEFAULT NULL, -- JSON: model weights used in ensemble
    ensemble_method TEXT DEFAULT 'weighted_average',
    ensemble_confidence REAL DEFAULT 0.0,
    
    -- Extended Data (JSON)
    base_metrics TEXT DEFAULT NULL,
    source_contributions TEXT DEFAULT NULL, -- LEGACY: backward compatibility
    ml_pipeline_data TEXT DEFAULT NULL,    -- LEGACY: backward compatibility
    market_data_details TEXT DEFAULT NULL
);

-- Create performance indexes for fast queries
CREATE INDEX idx_symbol_individual ON unified_predictions_individual(symbol);
CREATE INDEX idx_created_at_individual ON unified_predictions_individual(created_at);
CREATE INDEX idx_target_date_individual ON unified_predictions_individual(target_date);
CREATE INDEX idx_ensemble_id_individual ON unified_predictions_individual(ensemble_id);
CREATE INDEX idx_forecast_period_individual ON unified_predictions_individual(forecast_period_days);

-- Create compound indexes for complex queries
CREATE INDEX idx_symbol_period_individual ON unified_predictions_individual(symbol, forecast_period_days);
CREATE INDEX idx_symbol_target_individual ON unified_predictions_individual(symbol, target_date);

-- JSON validation constraints (SQLite 3.38+ feature)
-- Note: This requires newer SQLite versions, fallback to application-level validation

-- Insert example data for testing (4-Model structure)
INSERT INTO unified_predictions_individual (
    prediction_id,
    ensemble_id, 
    symbol,
    company_name,
    profit_forecast,
    confidence_level,
    forecast_period_days,
    recommendation,
    trend,
    target_date,
    created_at,
    individual_technical_prediction,
    individual_sentiment_prediction,
    individual_fundamental_prediction,
    individual_meta_prediction,
    ensemble_weights,
    risk_assessment,
    score
) VALUES (
    'pred_' || hex(randomblob(8)),
    'ensemble_' || hex(randomblob(8)),
    'AAPL',
    'Apple Inc.',
    8.5,
    0.82,
    30,
    'BUY',
    'BULLISH',
    datetime('now', '+30 days'),
    datetime('now'),
    '{"model_type": "technical", "prediction_values": [8.2], "confidence_score": 0.85, "volatility_estimate": 0.12, "horizon_days": 30}',
    '{"model_type": "sentiment", "prediction_values": [7.8], "confidence_score": 0.79, "volatility_estimate": 0.15, "horizon_days": 30}',
    '{"model_type": "fundamental", "prediction_values": [9.1], "confidence_score": 0.88, "volatility_estimate": 0.09, "horizon_days": 30}',
    '{"model_type": "meta", "prediction_values": [8.7], "confidence_score": 0.83, "volatility_estimate": 0.11, "horizon_days": 30}',
    '{"technical": 0.25, "sentiment": 0.20, "fundamental": 0.30, "meta": 0.25}',
    'MODERAT',
    0.82
);

-- Create view for easy individual model access
CREATE VIEW v_individual_model_predictions AS
SELECT 
    prediction_id,
    ensemble_id,
    symbol,
    company_name,
    profit_forecast as final_prediction,
    confidence_level as final_confidence,
    recommendation,
    risk_assessment,
    forecast_period_days,
    target_date,
    created_at,
    -- Parse individual predictions (requires JSON support)
    individual_technical_prediction as technical_model,
    individual_sentiment_prediction as sentiment_model,
    individual_fundamental_prediction as fundamental_model,
    individual_meta_prediction as meta_model,
    ensemble_weights,
    ensemble_method
FROM unified_predictions_individual
ORDER BY created_at DESC;

-- Create summary view for quick statistics
CREATE VIEW v_model_performance_summary AS
SELECT
    symbol,
    COUNT(*) as total_predictions,
    AVG(profit_forecast) as avg_predicted_profit,
    AVG(confidence_level) as avg_confidence,
    MAX(created_at) as last_prediction,
    COUNT(CASE WHEN individual_technical_prediction IS NOT NULL THEN 1 END) as technical_count,
    COUNT(CASE WHEN individual_sentiment_prediction IS NOT NULL THEN 1 END) as sentiment_count,
    COUNT(CASE WHEN individual_fundamental_prediction IS NOT NULL THEN 1 END) as fundamental_count,
    COUNT(CASE WHEN individual_meta_prediction IS NOT NULL THEN 1 END) as meta_count
FROM unified_predictions_individual
GROUP BY symbol
ORDER BY total_predictions DESC;

-- Success message
SELECT 'unified_predictions_individual schema created successfully with 4-model support' as result;