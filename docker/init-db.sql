-- Initialize Data Capsule Server database
-- This script runs on first container startup

-- Create the dcs schema
CREATE SCHEMA IF NOT EXISTS dcs;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA dcs TO dcs;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA dcs TO dcs;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA dcs TO dcs;

-- Set default search path for the dcs user
ALTER USER dcs SET search_path TO dcs, public;

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Data Capsule Server database initialized successfully';
END $$;
