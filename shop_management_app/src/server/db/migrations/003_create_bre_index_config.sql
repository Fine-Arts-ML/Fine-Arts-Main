-- Migration: 003_create_bre_index_config
-- Description: Create table to store the selected index directory configuration
-- Purpose: Persist the admin's choice of which Nextcloud directory to use as the index source

BEGIN;

-- bre_index_config: Store the selected index directory for re-indexing
CREATE TABLE IF NOT EXISTS bre_index_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(255) UNIQUE NOT NULL DEFAULT 'selected_index_path',
    config_value JSONB NOT NULL,
    description TEXT DEFAULT 'Selected index directory configuration',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bre_index_config_key ON bre_index_config(config_key);

-- Insert default config if not exists
INSERT INTO bre_index_config (config_key, config_value, description)
VALUES (
    'selected_index_path',
    '{"userId": null, "path": "", "storageId": null, "selectedAt": null}',
    'Currently selected index directory for re-indexing'
)
ON CONFLICT (config_key) DO NOTHING;

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_bre_index_config_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_bre_index_config_updated_at_trigger ON bre_index_config;
CREATE TRIGGER update_bre_index_config_updated_at_trigger
    BEFORE UPDATE ON bre_index_config
    FOR EACH ROW
    EXECUTE FUNCTION update_bre_index_config_updated_at();

COMMIT;
