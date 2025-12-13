-- Initialize Data Architecture Brain database
-- This script runs on first container startup

-- Create the dab schema
CREATE SCHEMA IF NOT EXISTS dab;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA dab TO dab;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA dab TO dab;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA dab TO dab;

-- Set default search path for the dab user
ALTER USER dab SET search_path TO dab, public;

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Data Architecture Brain database initialized successfully';
END $$;
