-- ===============================================================================
-- Enhanced Event-Store Functions für PostgreSQL Integration
-- Kompatibel mit Redis Event-Bus Data Flow
-- ===============================================================================

-- Function to append events (with automatic versioning and Redis compatibility)
CREATE OR REPLACE FUNCTION append_event(
    p_stream_id VARCHAR,
    p_aggregate_type VARCHAR,
    p_event_type VARCHAR,
    p_event_data JSONB,
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS UUID AS $$
DECLARE
    v_event_id UUID;
    v_current_version INTEGER;
    v_next_version INTEGER;
BEGIN
    -- Generate unique event ID
    v_event_id := gen_random_uuid();
    
    -- Get current version for the stream
    SELECT COALESCE(MAX(event_version), 0) INTO v_current_version
    FROM events 
    WHERE stream_id = p_stream_id;
    
    -- Calculate next version
    v_next_version := v_current_version + 1;
    
    -- Insert event with compatibility for existing schema
    INSERT INTO events (
        event_id, stream_id, aggregate_id, aggregate_type, 
        event_type, event_version, event_data, metadata
    ) VALUES (
        v_event_id, p_stream_id, p_stream_id, p_aggregate_type,
        p_event_type, v_next_version, p_event_data, p_metadata
    );
    
    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get stream events (for event sourcing)
CREATE OR REPLACE FUNCTION get_stream_events(
    p_stream_id VARCHAR,
    p_from_version INTEGER DEFAULT 1
)
RETURNS TABLE (
    event_id UUID,
    event_type VARCHAR,
    event_version INTEGER,
    event_data JSONB,
    metadata JSONB,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.event_id, e.event_type, e.event_version, 
        e.event_data, e.metadata, e.created_at
    FROM events e
    WHERE e.stream_id = p_stream_id
    AND e.event_version >= p_from_version
    ORDER BY e.event_version;
END;
$$ LANGUAGE plpgsql;

-- Enhanced UPSERT function for SOLL-IST tracking with Redis Event data
CREATE OR REPLACE FUNCTION upsert_soll_ist_tracking(
    p_datum DATE,
    p_symbol VARCHAR(10),
    p_unternehmen VARCHAR(255),
    p_ist_gewinn NUMERIC(10,4) DEFAULT NULL,
    p_soll_gewinn_1w NUMERIC(10,4) DEFAULT NULL,
    p_soll_gewinn_1m NUMERIC(10,4) DEFAULT NULL,
    p_soll_gewinn_3m NUMERIC(10,4) DEFAULT NULL,
    p_soll_gewinn_12m NUMERIC(10,4) DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_record_id INTEGER;
BEGIN
    -- UPSERT with RETURNING for integration tracking
    INSERT INTO soll_ist_gewinn_tracking (
        datum, symbol, unternehmen, ist_gewinn,
        soll_gewinn_1w, soll_gewinn_1m, soll_gewinn_3m, soll_gewinn_12m
    ) VALUES (
        p_datum, p_symbol, p_unternehmen, p_ist_gewinn,
        p_soll_gewinn_1w, p_soll_gewinn_1m, p_soll_gewinn_3m, p_soll_gewinn_12m
    )
    ON CONFLICT (datum, symbol) 
    DO UPDATE SET
        unternehmen = EXCLUDED.unternehmen,
        ist_gewinn = COALESCE(EXCLUDED.ist_gewinn, soll_ist_gewinn_tracking.ist_gewinn),
        soll_gewinn_1w = COALESCE(EXCLUDED.soll_gewinn_1w, soll_ist_gewinn_tracking.soll_gewinn_1w),
        soll_gewinn_1m = COALESCE(EXCLUDED.soll_gewinn_1m, soll_ist_gewinn_tracking.soll_gewinn_1m),
        soll_gewinn_3m = COALESCE(EXCLUDED.soll_gewinn_3m, soll_ist_gewinn_tracking.soll_gewinn_3m),
        soll_gewinn_12m = COALESCE(EXCLUDED.soll_gewinn_12m, soll_ist_gewinn_tracking.soll_gewinn_12m),
        updated_at = CURRENT_TIMESTAMP
    RETURNING id INTO v_record_id;
    
    RETURN v_record_id;
END;
$$ LANGUAGE plpgsql;

-- Function for Event-Bus triggered updates
CREATE OR REPLACE FUNCTION process_event_bus_data(
    p_event_type VARCHAR,
    p_event_data JSONB
)
RETURNS BOOLEAN AS $$
DECLARE
    v_success BOOLEAN := FALSE;
BEGIN
    -- Process different event types from Redis Event-Bus
    CASE p_event_type
        WHEN 'analysis.state.changed' THEN
            -- Handle analysis completion events
            IF p_event_data->>'state' = 'completed' AND p_event_data->>'symbol' IS NOT NULL THEN
                -- Update soll_ist_tracking if prediction data available
                PERFORM upsert_soll_ist_tracking(
                    CURRENT_DATE,
                    p_event_data->>'symbol',
                    COALESCE(p_event_data->>'company_name', p_event_data->>'symbol'),
                    NULL, -- ist_gewinn will be updated later
                    (p_event_data->'predictions'->>'soll_gewinn_1w')::numeric,
                    (p_event_data->'predictions'->>'soll_gewinn_1m')::numeric,
                    (p_event_data->'predictions'->>'soll_gewinn_3m')::numeric,
                    (p_event_data->'predictions'->>'soll_gewinn_12m')::numeric
                );
                v_success := TRUE;
            END IF;
            
        WHEN 'profit.calculation.completed' THEN
            -- Handle profit calculation events
            IF p_event_data->>'symbol' IS NOT NULL AND p_event_data->>'ist_gewinn' IS NOT NULL THEN
                PERFORM upsert_soll_ist_tracking(
                    CURRENT_DATE,
                    p_event_data->>'symbol',
                    COALESCE(p_event_data->>'company_name', p_event_data->>'symbol'),
                    (p_event_data->>'ist_gewinn')::numeric,
                    NULL, NULL, NULL, NULL  -- Keep existing SOLL values
                );
                v_success := TRUE;
            END IF;
            
        ELSE
            -- Log unknown event types for monitoring
            RAISE NOTICE 'Unknown event type for processing: %', p_event_type;
    END CASE;
    
    RETURN v_success;
END;
$$ LANGUAGE plpgsql;

-- Performance monitoring function for materialized views
CREATE OR REPLACE FUNCTION refresh_performance_views()
RETURNS TABLE (
    view_name TEXT,
    refresh_time_ms NUMERIC,
    record_count BIGINT
) AS $$
DECLARE
    v_start_time TIMESTAMP;
    v_end_time TIMESTAMP;
    v_duration_ms NUMERIC;
    v_count BIGINT;
BEGIN
    -- Stock Analysis Unified
    v_start_time := clock_timestamp();
    REFRESH MATERIALIZED VIEW CONCURRENTLY stock_analysis_unified;
    v_end_time := clock_timestamp();
    v_duration_ms := EXTRACT(MILLISECONDS FROM (v_end_time - v_start_time));
    SELECT count(*) INTO v_count FROM stock_analysis_unified;
    
    RETURN QUERY SELECT 'stock_analysis_unified'::TEXT, v_duration_ms, v_count;
    
    -- Portfolio Unified
    v_start_time := clock_timestamp();
    REFRESH MATERIALIZED VIEW CONCURRENTLY portfolio_unified;
    v_end_time := clock_timestamp();
    v_duration_ms := EXTRACT(MILLISECONDS FROM (v_end_time - v_start_time));
    SELECT count(*) INTO v_count FROM portfolio_unified;
    
    RETURN QUERY SELECT 'portfolio_unified'::TEXT, v_duration_ms, v_count;
    
    -- Trading Activity Unified
    v_start_time := clock_timestamp();
    REFRESH MATERIALIZED VIEW CONCURRENTLY trading_activity_unified;
    v_end_time := clock_timestamp();
    v_duration_ms := EXTRACT(MILLISECONDS FROM (v_end_time - v_start_time));
    SELECT count(*) INTO v_count FROM trading_activity_unified;
    
    RETURN QUERY SELECT 'trading_activity_unified'::TEXT, v_duration_ms, v_count;
    
    -- System Health Unified
    v_start_time := clock_timestamp();
    REFRESH MATERIALIZED VIEW CONCURRENTLY system_health_unified;
    v_end_time := clock_timestamp();
    v_duration_ms := EXTRACT(MILLISECONDS FROM (v_end_time - v_start_time));
    SELECT count(*) INTO v_count FROM system_health_unified;
    
    RETURN QUERY SELECT 'system_health_unified'::TEXT, v_duration_ms, v_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions for functions
GRANT EXECUTE ON FUNCTION append_event TO aktienanalyse;
GRANT EXECUTE ON FUNCTION get_stream_events TO aktienanalyse;
GRANT EXECUTE ON FUNCTION upsert_soll_ist_tracking TO aktienanalyse;
GRANT EXECUTE ON FUNCTION process_event_bus_data TO aktienanalyse;
GRANT EXECUTE ON FUNCTION refresh_performance_views TO aktienanalyse;

COMMENT ON FUNCTION append_event IS 'Thread-safe event appending compatible with Redis Event-Bus';
COMMENT ON FUNCTION upsert_soll_ist_tracking IS 'UPSERT function for SOLL-IST multi-horizon tracking';
COMMENT ON FUNCTION process_event_bus_data IS 'Processes events from Redis Event-Bus into PostgreSQL';
COMMENT ON FUNCTION refresh_performance_views IS 'Performance monitoring for materialized view refreshes';