-- ============================================================================
-- LEADFACTORY DATABASE INITIALIZATION
-- ============================================================================
-- This script initializes the PostgreSQL database for LeadFactory
-- Supports all PRPs with proper schema and extensions

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create database if not exists (handled by POSTGRES_DB env var)
-- Database: leadfactory

-- Set timezone
SET timezone = 'UTC';

-- Create schema for better organization
CREATE SCHEMA IF NOT EXISTS leadfactory;
CREATE SCHEMA IF NOT EXISTS assessments;
CREATE SCHEMA IF NOT EXISTS content;
CREATE SCHEMA IF NOT EXISTS reports;

-- Grant permissions to leadfactory user
GRANT ALL PRIVILEGES ON SCHEMA leadfactory TO leadfactory;
GRANT ALL PRIVILEGES ON SCHEMA assessments TO leadfactory;
GRANT ALL PRIVILEGES ON SCHEMA content TO leadfactory;
GRANT ALL PRIVILEGES ON SCHEMA reports TO leadfactory;

-- Set default search path
ALTER USER leadfactory SET search_path = leadfactory, assessments, content, reports, public;

-- Create custom types for assessments
CREATE TYPE assessment_status AS ENUM ('pending', 'in_progress', 'completed', 'failed', 'cancelled');
CREATE TYPE lead_source AS ENUM ('manual', 'import', 'api', 'webhook', 'scrape');
CREATE TYPE priority_level AS ENUM ('P1', 'P2', 'P3', 'P4');

-- Performance optimizations
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Create indexes for common queries (will be expanded with actual tables)
-- These will be created by Alembic migrations

-- Insert initial configuration data
INSERT INTO leadfactory.system_config (key, value, description) VALUES
    ('version', '1.0.0', 'LeadFactory system version'),
    ('max_concurrent_assessments', '10', 'Maximum concurrent assessments'),
    ('assessment_timeout_seconds', '300', 'Assessment timeout in seconds'),
    ('report_price_cents', '39900', 'Report price in cents ($399.00)')
ON CONFLICT (key) DO NOTHING;

-- Create function for updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'LeadFactory database initialized successfully';
    RAISE NOTICE 'Extensions enabled: uuid-ossp, pgcrypto, pg_trgm';
    RAISE NOTICE 'Schemas created: leadfactory, assessments, content, reports';
    RAISE NOTICE 'Ready for Alembic migrations';
END $$;