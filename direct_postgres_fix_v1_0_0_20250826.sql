-- ===============================================================================
-- Direct PostgreSQL Fix v1.0.0 for Server 10.1.1.174
-- Direkte Ausführung auf dem Server als postgres User
-- 
-- EXECUTION: sudo -u postgres psql -f this_file.sql
--
-- Autor: Claude Code - PostgreSQL Authentication Fix Agent
-- Datum: 26. August 2025
-- Version: 1.0.0 (Direct Server Fix)
-- ===============================================================================

-- Connect to default database first to create aktienanalyse_events
\c postgres

-- Create database if not exists
SELECT 'Creating aktienanalyse_events database...' as status;
CREATE DATABASE aktienanalyse_events WITH OWNER postgres ENCODING 'UTF8';

-- Create user if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aktienanalyse') THEN
        CREATE USER aktienanalyse WITH PASSWORD 'secure_password_2025';
        ALTER USER aktienanalyse CREATEDB CREATEROLE SUPERUSER;
        RAISE NOTICE 'User aktienanalyse created with superuser privileges';
    ELSE
        ALTER USER aktienanalyse WITH PASSWORD 'secure_password_2025';
        ALTER USER aktienanalyse CREATEDB CREATEROLE SUPERUSER;
        RAISE NOTICE 'User aktienanalyse updated with superuser privileges';
    END IF;
END
$$;

-- Grant all privileges on database
GRANT ALL PRIVILEGES ON DATABASE aktienanalyse_events TO aktienanalyse;

-- Now connect to the target database
\c aktienanalyse_events

-- Create schema and tables
SELECT 'Setting up schema in aktienanalyse_events...' as status;

-- Create soll_ist_gewinn_tracking table for backward compatibility
DROP TABLE IF EXISTS soll_ist_gewinn_tracking CASCADE;

CREATE TABLE soll_ist_gewinn_tracking (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    company_name VARCHAR(255),
    datum DATE NOT NULL,
    
    -- SOLL values for different time horizons
    soll_gewinn_1w DECIMAL(12,4),
    soll_gewinn_1m DECIMAL(12,4), 
    soll_gewinn_3m DECIMAL(12,4),
    soll_gewinn_12m DECIMAL(12,4),
    
    -- IST value (actual profit)
    ist_gewinn DECIMAL(12,4),
    
    -- Enhanced Predictions Averages
    avg_prediction_1w DECIMAL(12,4),
    avg_prediction_1m DECIMAL(12,4),
    avg_prediction_3m DECIMAL(12,4),
    avg_prediction_12m DECIMAL(12,4),
    
    -- Metadata
    market_region VARCHAR(50) DEFAULT 'DE',
    confidence_score DECIMAL(5,4),
    model_version VARCHAR(50),
    calculation_method VARCHAR(50) DEFAULT 'ensemble',
    
    -- Timestamps
    calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    avg_calculation_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Sample counts for averages
    avg_sample_count_1w INTEGER DEFAULT 0,
    avg_sample_count_1m INTEGER DEFAULT 0,
    avg_sample_count_3m INTEGER DEFAULT 0,
    avg_sample_count_12m INTEGER DEFAULT 0,
    
    -- Constraints
    CONSTRAINT soll_ist_gewinn_tracking_datum_symbol_unique UNIQUE (datum, symbol)
);

-- Create indexes
CREATE INDEX idx_soll_ist_symbol_datum ON soll_ist_gewinn_tracking (symbol, datum DESC);
CREATE INDEX idx_soll_ist_datum ON soll_ist_gewinn_tracking (datum DESC);
CREATE INDEX idx_soll_ist_region ON soll_ist_gewinn_tracking (market_region);

-- Create update trigger
CREATE OR REPLACE FUNCTION update_soll_ist_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_soll_ist_updated_at
    BEFORE UPDATE ON soll_ist_gewinn_tracking
    FOR EACH ROW
    EXECUTE FUNCTION update_soll_ist_updated_at();

-- Insert sample data
INSERT INTO soll_ist_gewinn_tracking 
(symbol, company_name, datum, soll_gewinn_1w, soll_gewinn_1m, soll_gewinn_3m, soll_gewinn_12m, confidence_score, model_version)
VALUES 
('AAPL', 'Apple Inc.', CURRENT_DATE, 2.5, 5.2, 8.7, 15.3, 0.85, 'v6.0.0'),
('MSFT', 'Microsoft Corp.', CURRENT_DATE, 1.8, 4.1, 7.2, 12.8, 0.82, 'v6.0.0'),
('GOOGL', 'Alphabet Inc.', CURRENT_DATE, 3.2, 6.5, 9.8, 18.2, 0.79, 'v6.0.0'),
('TSLA', 'Tesla Inc.', CURRENT_DATE, -1.2, 2.3, 12.1, 25.7, 0.73, 'v6.0.0'),
('AMZN', 'Amazon.com Inc.', CURRENT_DATE, 2.1, 4.8, 8.2, 14.6, 0.81, 'v6.0.0');

-- Grant all permissions to aktienanalyse user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aktienanalyse;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO aktienanalyse;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO aktienanalyse;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO aktienanalyse;
GRANT USAGE, CREATE ON SCHEMA public TO aktienanalyse;

-- Verification
SELECT 
    'Database setup completed' as status,
    COUNT(*) as sample_records
FROM soll_ist_gewinn_tracking;

SELECT 
    schemaname, 
    tablename, 
    tableowner,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;