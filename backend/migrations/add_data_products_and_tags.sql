-- Migration: Add Data Products and Tag enhancements
-- Date: 2025-12-16
-- Description: Adds data_products table, tag associations, and sensitivity_level column

-- 1. Add sensitivity_level column to tags table
ALTER TABLE dab.tags
ADD COLUMN IF NOT EXISTS sensitivity_level VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_tags_sensitivity_level ON dab.tags(sensitivity_level);

-- 2. Create data_products table
CREATE TABLE IF NOT EXISTS dab.data_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    domain_id UUID REFERENCES dab.domains(id),
    owner_id UUID REFERENCES dab.owners(id),
    slo_freshness_hours INTEGER,
    slo_availability_percent FLOAT,
    slo_quality_threshold FLOAT,
    output_port_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    input_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Add indexes for data_products
CREATE INDEX IF NOT EXISTS idx_data_products_domain_id ON dab.data_products(domain_id);
CREATE INDEX IF NOT EXISTS idx_data_products_owner_id ON dab.data_products(owner_id);
CREATE INDEX IF NOT EXISTS idx_data_products_status ON dab.data_products(status);

-- Add unique constraint on name
CREATE UNIQUE INDEX IF NOT EXISTS uq_data_product_name ON dab.data_products(name);

-- 3. Create capsule_data_products association table (PART_OF edge)
CREATE TABLE IF NOT EXISTS dab.capsule_data_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capsule_id UUID NOT NULL REFERENCES dab.capsules(id) ON DELETE CASCADE,
    data_product_id UUID NOT NULL REFERENCES dab.data_products(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Add indexes for capsule_data_products
CREATE INDEX IF NOT EXISTS idx_capsule_data_products_capsule_id ON dab.capsule_data_products(capsule_id);
CREATE INDEX IF NOT EXISTS idx_capsule_data_products_data_product_id ON dab.capsule_data_products(data_product_id);

-- Add unique constraint to prevent duplicate associations
CREATE UNIQUE INDEX IF NOT EXISTS uq_capsule_data_product ON dab.capsule_data_products(capsule_id, data_product_id);

-- 4. Create capsule_tags association table (TAGGED_WITH edge)
CREATE TABLE IF NOT EXISTS dab.capsule_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capsule_id UUID NOT NULL REFERENCES dab.capsules(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES dab.tags(id) ON DELETE CASCADE,
    added_by VARCHAR(255),
    added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    meta JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Add indexes for capsule_tags
CREATE INDEX IF NOT EXISTS idx_capsule_tags_capsule_id ON dab.capsule_tags(capsule_id);
CREATE INDEX IF NOT EXISTS idx_capsule_tags_tag_id ON dab.capsule_tags(tag_id);

-- Add unique constraint to prevent duplicate tags on same capsule
CREATE UNIQUE INDEX IF NOT EXISTS uq_capsule_tag ON dab.capsule_tags(capsule_id, tag_id);

-- 5. Create column_tags association table (TAGGED_WITH edge)
CREATE TABLE IF NOT EXISTS dab.column_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    column_id UUID NOT NULL REFERENCES dab.columns(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES dab.tags(id) ON DELETE CASCADE,
    added_by VARCHAR(255),
    added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    meta JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Add indexes for column_tags
CREATE INDEX IF NOT EXISTS idx_column_tags_column_id ON dab.column_tags(column_id);
CREATE INDEX IF NOT EXISTS idx_column_tags_tag_id ON dab.column_tags(tag_id);

-- Add unique constraint to prevent duplicate tags on same column
CREATE UNIQUE INDEX IF NOT EXISTS uq_column_tag ON dab.column_tags(column_id, tag_id);

-- Add comments for documentation
COMMENT ON TABLE dab.data_products IS 'Data products grouping capsules in Data Mesh architecture';
COMMENT ON TABLE dab.capsule_data_products IS 'PART_OF edges between capsules and data products';
COMMENT ON TABLE dab.capsule_tags IS 'TAGGED_WITH edges between capsules and tags';
COMMENT ON TABLE dab.column_tags IS 'TAGGED_WITH edges between columns and tags';

COMMENT ON COLUMN dab.data_products.slo_freshness_hours IS 'Max hours since last data update';
COMMENT ON COLUMN dab.data_products.slo_availability_percent IS 'Target availability (e.g., 99.9)';
COMMENT ON COLUMN dab.data_products.slo_quality_threshold IS 'Min conformance score (0.0 to 1.0)';
