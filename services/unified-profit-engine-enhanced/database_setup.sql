-- ============================================================================
-- Database Setup für Unified Profit Engine Enhanced v6.0.0
-- Clean Architecture Database Schema
-- ============================================================================

-- Profit Predictions Table
CREATE TABLE IF NOT EXISTS profit_predictions (
    id UUID PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    market_region VARCHAR(50) NOT NULL,
    target_date DATE NOT NULL,
    forecasts_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT profit_predictions_symbol_target_unique UNIQUE (symbol, target_date)
);

-- SOLL-IST Tracking Table (Enhanced from LLD v6.0)
CREATE TABLE IF NOT EXISTS soll_ist_gewinn_tracking (
    id UUID PRIMARY KEY,
    datum DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    unternehmen VARCHAR(255) NOT NULL,
    market_region VARCHAR(50),
    ist_gewinn DECIMAL(12,4),
    soll_gewinn_1w DECIMAL(12,4),
    soll_gewinn_1m DECIMAL(12,4), 
    soll_gewinn_3m DECIMAL(12,4),
    soll_gewinn_12m DECIMAL(12,4),
    
    -- Calculated columns für Performance Analysis
    diff_1w DECIMAL(12,4) GENERATED ALWAYS AS (ist_gewinn - soll_gewinn_1w) STORED,
    diff_1m DECIMAL(12,4) GENERATED ALWAYS AS (ist_gewinn - soll_gewinn_1m) STORED,
    diff_3m DECIMAL(12,4) GENERATED ALWAYS AS (ist_gewinn - soll_gewinn_3m) STORED,
    diff_12m DECIMAL(12,4) GENERATED ALWAYS AS (ist_gewinn - soll_gewinn_12m) STORED,
    
    -- Metadata
    confidence_1w DECIMAL(5,4),
    confidence_1m DECIMAL(5,4),
    confidence_3m DECIMAL(5,4),
    confidence_12m DECIMAL(5,4),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT soll_ist_gewinn_tracking_datum_symbol_unique UNIQUE (datum, symbol)
);

-- Event Store Table für Event Persistence
CREATE TABLE IF NOT EXISTS event_store (
    event_id UUID PRIMARY KEY,
    correlation_id UUID NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    event_data JSONB NOT NULL,
    metadata JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes für Performance Optimization
CREATE INDEX IF NOT EXISTS idx_profit_predictions_symbol_target ON profit_predictions (symbol, target_date DESC);
CREATE INDEX IF NOT EXISTS idx_profit_predictions_created ON profit_predictions (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_soll_ist_symbol_datum ON soll_ist_gewinn_tracking (symbol, datum DESC);
CREATE INDEX IF NOT EXISTS idx_soll_ist_datum ON soll_ist_gewinn_tracking (datum DESC);
CREATE INDEX IF NOT EXISTS idx_soll_ist_region ON soll_ist_gewinn_tracking (market_region);

CREATE INDEX IF NOT EXISTS idx_event_store_type ON event_store (event_type);
CREATE INDEX IF NOT EXISTS idx_event_store_correlation ON event_store (correlation_id);
CREATE INDEX IF NOT EXISTS idx_event_store_created ON event_store (created_at DESC);

-- Performance Analysis Views (entspricht LLD v6.0)
CREATE OR REPLACE VIEW v_multi_horizon_performance AS
SELECT 
    symbol,
    unternehmen,
    market_region,
    datum,
    ist_gewinn,
    
    -- SOLL Values
    soll_gewinn_1w, soll_gewinn_1m, soll_gewinn_3m, soll_gewinn_12m,
    
    -- Performance Differences
    diff_1w, diff_1m, diff_3m, diff_12m,
    
    -- Performance Percentages
    CASE WHEN soll_gewinn_1w != 0 THEN (diff_1w / soll_gewinn_1w) * 100 END as perf_1w_pct,
    CASE WHEN soll_gewinn_1m != 0 THEN (diff_1m / soll_gewinn_1m) * 100 END as perf_1m_pct,
    CASE WHEN soll_gewinn_3m != 0 THEN (diff_3m / soll_gewinn_3m) * 100 END as perf_3m_pct,
    CASE WHEN soll_gewinn_12m != 0 THEN (diff_12m / soll_gewinn_12m) * 100 END as perf_12m_pct,
    
    -- Confidence Metrics
    confidence_1w, confidence_1m, confidence_3m, confidence_12m,
    
    updated_at
FROM soll_ist_gewinn_tracking
WHERE ist_gewinn IS NOT NULL;

-- Best Performing Predictions View
CREATE OR REPLACE VIEW v_best_predictions AS
SELECT 
    symbol,
    unternehmen, 
    datum,
    
    -- Best performing horizon
    CASE 
        WHEN ABS(diff_1w) = LEAST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) THEN '1W'
        WHEN ABS(diff_1m) = LEAST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) THEN '1M'
        WHEN ABS(diff_3m) = LEAST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) THEN '3M'
        ELSE '12M'
    END as best_horizon,
    
    LEAST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) as best_accuracy,
    
    -- Worst performing horizon
    CASE 
        WHEN ABS(diff_1w) = GREATEST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) THEN '1W'
        WHEN ABS(diff_1m) = GREATEST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) THEN '1M'
        WHEN ABS(diff_3m) = GREATEST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) THEN '3M'
        ELSE '12M'
    END as worst_horizon,
    
    GREATEST(ABS(diff_1w), ABS(diff_1m), ABS(diff_3m), ABS(diff_12m)) as worst_accuracy
    
FROM soll_ist_gewinn_tracking
WHERE ist_gewinn IS NOT NULL
  AND (diff_1w IS NOT NULL OR diff_1m IS NOT NULL OR diff_3m IS NOT NULL OR diff_12m IS NOT NULL);

-- Updated_at Trigger Function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Updated_at Triggers
DROP TRIGGER IF EXISTS update_soll_ist_tracking_updated_at ON soll_ist_gewinn_tracking;
CREATE TRIGGER update_soll_ist_tracking_updated_at
    BEFORE UPDATE ON soll_ist_gewinn_tracking
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_profit_predictions_updated_at ON profit_predictions;
CREATE TRIGGER update_profit_predictions_updated_at
    BEFORE UPDATE ON profit_predictions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();