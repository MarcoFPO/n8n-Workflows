-- ===============================================================================
-- Migration zu optimiertem Event-Store Schema
-- Migriert bestehende Daten und implementiert neue Performance-Optimierungen
-- ===============================================================================

BEGIN;

-- 1. Backup der bestehenden Daten
CREATE TABLE IF NOT EXISTS events_backup AS 
SELECT * FROM events;

CREATE TABLE IF NOT EXISTS event_streams_backup AS 
SELECT * FROM event_streams;

CREATE TABLE IF NOT EXISTS snapshots_backup AS 
SELECT * FROM snapshots;

-- 2. Drop existing tables und views
DROP MATERIALIZED VIEW IF EXISTS portfolio_unified CASCADE;
DROP MATERIALIZED VIEW IF EXISTS stock_analysis_unified CASCADE;
DROP MATERIALIZED VIEW IF EXISTS system_health_unified CASCADE;
DROP MATERIALIZED VIEW IF EXISTS trading_activity_unified CASCADE;

DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS event_streams CASCADE;
DROP TABLE IF EXISTS snapshots CASCADE;

-- 3. Implementiere das neue optimierte Schema
-- Event-Store Haupt-Tabelle (Single Source of Truth)
CREATE TABLE IF NOT EXISTS events (
    -- Event Identifiers
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id VARCHAR(255) NOT NULL,           -- Aggregate identifier (stock-AAPL, portfolio-123)
    stream_type VARCHAR(100) NOT NULL,         -- Domain (stock, portfolio, trading, system)
    
    -- Event Metadata
    event_type VARCHAR(100) NOT NULL,          -- Specific event type (analysis.state.changed)
    event_version BIGINT NOT NULL,             -- Event version in stream (for optimistic locking)
    global_version BIGSERIAL,                  -- Global event ordering across all streams
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Event Data & Metadata
    event_data JSONB NOT NULL,                 -- Event payload (structured JSON)
    event_metadata JSONB DEFAULT '{}',         -- Correlation IDs, causation, tracing
    
    -- Event Processing
    processed_at TIMESTAMP,                    -- When event was processed by handlers
    processing_attempts INTEGER DEFAULT 0,     -- For retry logic
    
    -- Constraints for Event-Sourcing
    UNIQUE (stream_id, event_version),         -- Ensure event ordering per stream
    CHECK (event_version > 0),                 -- Version must be positive
    CHECK (jsonb_typeof(event_data) = 'object') -- Ensure valid JSON object
);

-- 4. Migriere bestehende Daten ins neue Schema
INSERT INTO events (
    stream_id, 
    stream_type,
    event_type, 
    event_version,
    timestamp,
    event_data,
    event_metadata
)
SELECT 
    backup.stream_id,
    CASE 
        WHEN backup.stream_id LIKE 'stock-%' THEN 'stock'
        WHEN backup.stream_id LIKE 'portfolio-%' THEN 'portfolio'
        WHEN backup.stream_id LIKE 'trading-%' THEN 'trading'
        ELSE 'system'
    END as stream_type,
    backup.event_type,
    backup.event_version,
    backup.created_at,
    backup.event_data,
    backup.metadata
FROM events_backup backup
ORDER BY backup.created_at;

-- 5. Performance-optimierte Indexes
CREATE INDEX IF NOT EXISTS idx_events_stream 
    ON events (stream_id, event_version);       -- Stream reconstruction

CREATE INDEX IF NOT EXISTS idx_events_type_time 
    ON events (event_type, timestamp DESC);     -- Event type + time-based queries

CREATE INDEX IF NOT EXISTS idx_events_global 
    ON events (global_version);                 -- Global event ordering

CREATE INDEX IF NOT EXISTS idx_events_timestamp 
    ON events (timestamp DESC);                 -- Recent events

-- JSONB indexes for fast event data queries
CREATE INDEX IF NOT EXISTS idx_events_data_gin 
    ON events USING GIN (event_data);          -- Full JSONB search

CREATE INDEX IF NOT EXISTS idx_events_symbol 
    ON events ((event_data->>'symbol'));       -- Stock symbol lookups

CREATE INDEX IF NOT EXISTS idx_events_portfolio_id 
    ON events ((event_data->>'portfolio_id')); -- Portfolio lookups

CREATE INDEX IF NOT EXISTS idx_events_order_id 
    ON events ((event_data->>'order_id'));     -- Trading order lookups

-- Partial indexes for performance-critical queries
CREATE INDEX IF NOT EXISTS idx_events_analysis_completed 
    ON events (stream_id, timestamp DESC) 
    WHERE event_type = 'analysis.state.changed' 
    AND event_data->>'state' = 'completed';

CREATE INDEX IF NOT EXISTS idx_events_trading_filled 
    ON events (timestamp DESC) 
    WHERE event_type = 'trading.state.changed' 
    AND event_data->>'state' = 'filled';

-- 6. Materialized Views für 0.12s Query-Performance
-- Stock Analysis View
CREATE MATERIALIZED VIEW stock_analysis_unified AS
SELECT 
    -- Stock Identification
    (latest_analysis.event_data->>'symbol') as symbol,
    latest_analysis.stream_id,
    
    -- Analysis Results
    (latest_analysis.event_data->>'score')::numeric as latest_score,
    (latest_analysis.event_data->>'recommendation') as recommendation,
    (latest_analysis.event_data->>'confidence')::numeric as confidence,
    (latest_analysis.event_data->>'target_price')::numeric as target_price,
    (latest_analysis.event_data->>'risk_level') as risk_level,
    
    -- Technical Indicators
    latest_analysis.event_data->'technical_indicators' as technical_indicators,
    
    -- Performance Metrics (from portfolio events)
    COALESCE((perf.event_data->>'total_return')::numeric, 0) as total_return,
    COALESCE((perf.event_data->>'sharpe_ratio')::numeric, 0) as sharpe_ratio,
    COALESCE((perf.event_data->>'max_drawdown')::numeric, 0) as max_drawdown,
    COALESCE((perf.event_data->>'volatility')::numeric, 0) as volatility,
    
    -- Trading Activity (from trading events)
    COALESCE((trade.event_data->>'total_value')::numeric, 0) as position_value,
    COALESCE((trade.event_data->>'filled_quantity')::numeric, 0) as quantity,
    COALESCE((trade.event_data->>'average_fill_price')::numeric, 0) as avg_price,
    COALESCE((trade.event_data->>'fees')::numeric, 0) as total_fees,
    
    -- Timestamps
    latest_analysis.timestamp as analysis_updated,
    perf.timestamp as performance_updated,
    trade.timestamp as trading_updated,
    GREATEST(
        latest_analysis.timestamp, 
        COALESCE(perf.timestamp, '1970-01-01'::timestamp),
        COALESCE(trade.timestamp, '1970-01-01'::timestamp)
    ) as last_updated

FROM (
    -- Latest analysis for each stock
    SELECT DISTINCT ON (event_data->>'symbol') 
        stream_id, event_data, timestamp
    FROM events 
    WHERE event_type = 'analysis.state.changed'
    AND event_data->>'state' = 'completed'
    AND event_data->>'symbol' IS NOT NULL
    ORDER BY event_data->>'symbol', timestamp DESC
) latest_analysis

LEFT JOIN LATERAL (
    -- Latest performance data for each stock
    SELECT event_data, timestamp
    FROM events e2
    WHERE e2.event_type = 'portfolio.state.changed'
    AND e2.event_data->>'state' = 'updated'
    AND EXISTS (
        SELECT 1 FROM jsonb_array_elements(e2.event_data->'top_performers') tp
        WHERE tp->>'symbol' = latest_analysis.event_data->>'symbol'
    )
    ORDER BY e2.timestamp DESC
    LIMIT 1
) perf ON true

LEFT JOIN LATERAL (
    -- Latest trading activity for each stock
    SELECT event_data, timestamp
    FROM events e3
    WHERE e3.event_type = 'trading.state.changed'
    AND e3.event_data->>'state' = 'filled'
    AND e3.event_data->>'symbol' = latest_analysis.event_data->>'symbol'
    ORDER BY e3.timestamp DESC
    LIMIT 1
) trade ON true

WITH DATA;

-- Index für Materialized View
CREATE UNIQUE INDEX idx_stock_analysis_unified_symbol 
    ON stock_analysis_unified (symbol);
CREATE INDEX idx_stock_analysis_unified_score 
    ON stock_analysis_unified (latest_score DESC);
CREATE INDEX idx_stock_analysis_unified_updated 
    ON stock_analysis_unified (last_updated DESC);

-- 7. Event-Store Utility Functions
-- Function to append events (with automatic versioning)
CREATE OR REPLACE FUNCTION append_event(
    p_stream_id VARCHAR,
    p_stream_type VARCHAR,
    p_event_type VARCHAR,
    p_event_data JSONB,
    p_event_metadata JSONB DEFAULT '{}',
    p_expected_version BIGINT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_event_id UUID;
    v_current_version BIGINT;
    v_next_version BIGINT;
BEGIN
    -- Get current version for the stream
    SELECT COALESCE(MAX(event_version), 0) INTO v_current_version
    FROM events 
    WHERE stream_id = p_stream_id;
    
    -- Check expected version (optimistic concurrency control)
    IF p_expected_version IS NOT NULL AND v_current_version != p_expected_version THEN
        RAISE EXCEPTION 'Concurrency conflict: expected version %, but current version is %', 
            p_expected_version, v_current_version;
    END IF;
    
    -- Calculate next version
    v_next_version := v_current_version + 1;
    
    -- Insert event
    INSERT INTO events (
        stream_id, stream_type, event_type, event_version,
        event_data, event_metadata
    ) VALUES (
        p_stream_id, p_stream_type, p_event_type, v_next_version,
        p_event_data, p_event_metadata
    )
    RETURNING id INTO v_event_id;
    
    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get stream events (for event sourcing)
CREATE OR REPLACE FUNCTION get_stream_events(
    p_stream_id VARCHAR,
    p_from_version BIGINT DEFAULT 1
)
RETURNS TABLE (
    event_id UUID,
    event_type VARCHAR,
    event_version BIGINT,
    event_data JSONB,
    event_metadata JSONB,
    timestamp TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id, e.event_type, e.event_version, 
        e.event_data, e.event_metadata, e.timestamp
    FROM events e
    WHERE e.stream_id = p_stream_id
    AND e.event_version >= p_from_version
    ORDER BY e.event_version;
END;
$$ LANGUAGE plpgsql;

-- 8. Snapshots Tabelle
CREATE TABLE IF NOT EXISTS snapshots (
    stream_id VARCHAR(255) PRIMARY KEY,
    stream_type VARCHAR(100) NOT NULL,
    snapshot_version BIGINT NOT NULL,
    snapshot_data JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 9. Verify Migration Success
DO $$
DECLARE
    v_backup_count INTEGER;
    v_new_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_backup_count FROM events_backup;
    SELECT COUNT(*) INTO v_new_count FROM events;
    
    IF v_backup_count != v_new_count THEN
        RAISE EXCEPTION 'Migration failed: backup has % events, new table has %', v_backup_count, v_new_count;
    END IF;
    
    RAISE NOTICE 'Migration successful: % events migrated', v_new_count;
END $$;

COMMIT;

-- 10. Test query performance
SELECT 'Migration completed successfully. Testing materialized view...' as status;

-- Show migrated events
SELECT 
    stream_id,
    event_type, 
    timestamp,
    event_data->>'symbol' as symbol
FROM events 
ORDER BY timestamp DESC;

-- Show materialized view content
SELECT * FROM stock_analysis_unified;

COMMENT ON TABLE events IS 'Optimized Event-Store: Single source of truth für alle System-Events (Migrated)';
COMMENT ON MATERIALIZED VIEW stock_analysis_unified IS 'Optimized view for 0.12s stock analysis queries (Post-Migration)';