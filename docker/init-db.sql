-- Database initialization script for PostgreSQL
-- This script ensures the leadfactory database exists

-- Create the database if it doesn't exist
SELECT 'CREATE DATABASE leadfactory'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'leadfactory')\gexec

-- Grant permissions to the leadfactory user
GRANT ALL PRIVILEGES ON DATABASE leadfactory TO leadfactory;

-- Connect to the leadfactory database to ensure it's properly initialized
\c leadfactory;

-- Create any necessary extensions (if needed)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set default permissions for future tables
ALTER DEFAULT PRIVILEGES FOR USER leadfactory IN SCHEMA public GRANT ALL ON TABLES TO leadfactory;
ALTER DEFAULT PRIVILEGES FOR USER leadfactory IN SCHEMA public GRANT ALL ON SEQUENCES TO leadfactory;
ALTER DEFAULT PRIVILEGES FOR USER leadfactory IN SCHEMA public GRANT ALL ON FUNCTIONS TO leadfactory;