-- ===============================================================================
-- Testdaten für ml_predictions Tabelle - Enhanced Predictions Averages Demo
-- Erstellt realistische KI-Prognosen für GUI-Demonstration
-- 
-- Ziel: Durchschnittswerte in KI-Prognosen GUI anzeigen können
-- Datum: 26. August 2025
-- ===============================================================================

-- Sample ML Predictions für verschiedene Symbole und Zeiträume
INSERT INTO ml_predictions (prediction_id, symbol, prediction_type, prediction_data, ensemble_confidence)
VALUES 
    -- AAPL Predictions (1W Horizon)
    ('pred_aapl_001', 'AAPL', 'ensemble', '{
        "predicted_value": 185.50,
        "target_price": 190.00,
        "horizon_days": 7,
        "model_name": "ensemble_v1",
        "confidence": 0.82,
        "features_used": ["technical", "fundamental", "sentiment"]
    }', 0.82),
    
    ('pred_aapl_002', 'AAPL', 'ensemble', '{
        "predicted_value": 187.20,
        "target_price": 192.50,
        "horizon_days": 7,
        "model_name": "ensemble_v1",
        "confidence": 0.85,
        "features_used": ["technical", "fundamental", "sentiment"]
    }', 0.85),
    
    ('pred_aapl_003', 'AAPL', 'ensemble', '{
        "predicted_value": 183.80,
        "target_price": 188.00,
        "horizon_days": 7,
        "model_name": "ensemble_v1",
        "confidence": 0.78,
        "features_used": ["technical", "fundamental", "sentiment"]
    }', 0.78),
    
    -- AAPL Predictions (1M Horizon)
    ('pred_aapl_1m_001', 'AAPL', 'ensemble', '{
        "predicted_value": 195.00,
        "target_price": 200.00,
        "horizon_days": 30,
        "model_name": "ensemble_v1",
        "confidence": 0.75,
        "features_used": ["technical", "fundamental", "sentiment", "macro"]
    }', 0.75),
    
    ('pred_aapl_1m_002', 'AAPL', 'ensemble', '{
        "predicted_value": 198.50,
        "target_price": 205.00,
        "horizon_days": 30,
        "model_name": "ensemble_v1",
        "confidence": 0.79,
        "features_used": ["technical", "fundamental", "sentiment", "macro"]
    }', 0.79),
    
    -- MSFT Predictions (1W Horizon)
    ('pred_msft_001', 'MSFT', 'ensemble', '{
        "predicted_value": 338.20,
        "target_price": 345.00,
        "horizon_days": 7,
        "model_name": "ensemble_v1",
        "confidence": 0.80,
        "features_used": ["technical", "fundamental", "sentiment"]
    }', 0.80),
    
    ('pred_msft_002', 'MSFT', 'ensemble', '{
        "predicted_value": 341.50,
        "target_price": 348.00,
        "horizon_days": 7,
        "model_name": "ensemble_v1",
        "confidence": 0.83,
        "features_used": ["technical", "fundamental", "sentiment"]
    }', 0.83),
    
    ('pred_msft_003', 'MSFT', 'ensemble', '{
        "predicted_value": 335.80,
        "target_price": 342.00,
        "horizon_days": 7,
        "model_name": "ensemble_v1",
        "confidence": 0.77,
        "features_used": ["technical", "fundamental", "sentiment"]
    }', 0.77),
    
    -- GOOGL Predictions (1M Horizon)
    ('pred_googl_1m_001', 'GOOGL', 'ensemble', '{
        "predicted_value": 142.80,
        "target_price": 150.00,
        "horizon_days": 30,
        "model_name": "ensemble_v1",
        "confidence": 0.72,
        "features_used": ["technical", "fundamental", "sentiment", "macro"]
    }', 0.72),
    
    ('pred_googl_1m_002', 'GOOGL', 'ensemble', '{
        "predicted_value": 145.20,
        "target_price": 152.00,
        "horizon_days": 30,
        "model_name": "ensemble_v1",
        "confidence": 0.76,
        "features_used": ["technical", "fundamental", "sentiment", "macro"]
    }', 0.76),
    
    -- TESLA Predictions (3M Horizon)
    ('pred_tsla_3m_001', 'TSLA', 'ensemble', '{
        "predicted_value": 245.00,
        "target_price": 260.00,
        "horizon_days": 90,
        "model_name": "ensemble_v1",
        "confidence": 0.65,
        "features_used": ["technical", "fundamental", "sentiment", "macro", "sector"]
    }', 0.65),
    
    ('pred_tsla_3m_002', 'TSLA', 'ensemble', '{
        "predicted_value": 252.30,
        "target_price": 265.00,
        "horizon_days": 90,
        "model_name": "ensemble_v1",
        "confidence": 0.68,
        "features_used": ["technical", "fundamental", "sentiment", "macro", "sector"]
    }', 0.68),
    
    -- NVDA Predictions (verschiedene Horizonte)
    ('pred_nvda_1w_001', 'NVDA', 'ensemble', '{
        "predicted_value": 485.50,
        "target_price": 495.00,
        "horizon_days": 7,
        "model_name": "ensemble_v1",
        "confidence": 0.84,
        "features_used": ["technical", "fundamental", "sentiment"]
    }', 0.84),
    
    ('pred_nvda_1m_001', 'NVDA', 'ensemble', '{
        "predicted_value": 520.00,
        "target_price": 540.00,
        "horizon_days": 30,
        "model_name": "ensemble_v1",
        "confidence": 0.81,
        "features_used": ["technical", "fundamental", "sentiment", "macro"]
    }', 0.81),
    
    -- META Predictions
    ('pred_meta_1w_001', 'META', 'ensemble', '{
        "predicted_value": 318.20,
        "target_price": 325.00,
        "horizon_days": 7,
        "model_name": "ensemble_v1",
        "confidence": 0.79,
        "features_used": ["technical", "fundamental", "sentiment"]
    }', 0.79),
    
    ('pred_meta_1w_002', 'META', 'ensemble', '{
        "predicted_value": 321.80,
        "target_price": 328.00,
        "horizon_days": 7,
        "model_name": "ensemble_v1",
        "confidence": 0.82,
        "features_used": ["technical", "fundamental", "sentiment"]
    }', 0.82);

-- Refresh Materialized View nach Dateninsert
SELECT refresh_ki_prognosen_averages_mv();

-- Validierung der Testdaten
SELECT 
    'Testdaten erfolgreich eingefügt' as status,
    COUNT(*) as total_predictions,
    COUNT(DISTINCT symbol) as unique_symbols,
    MIN(created_at) as earliest_prediction,
    MAX(created_at) as latest_prediction
FROM ml_predictions;

-- Anzeige der generierten Durchschnittswerte
SELECT 
    symbol,
    timeframe,
    prediction_count,
    ROUND(avg_predicted_value::numeric, 2) as avg_predicted_value,
    ROUND(avg_confidence::numeric, 3) as avg_confidence,
    ROUND(predicted_value_stddev::numeric, 2) as stddev
FROM mv_ki_prognosen_averages
ORDER BY symbol, timeframe;