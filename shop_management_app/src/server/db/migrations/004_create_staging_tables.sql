-- Migration: 004_create_staging_tables
-- Description: Create tables for session-based tag and description staging
-- Purpose: Allow users to stage AI-generated tags and descriptions before pushing to production

BEGIN;

-- =============================================================================
-- 1. bre_tags_staging: Stores unique staged tag values per session
-- =============================================================================
CREATE TABLE IF NOT EXISTS bre_tags_staging (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(128) NOT NULL,
    name VARCHAR(255) NOT NULL,
    visibility INTEGER NOT NULL DEFAULT 1,
    editable INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, name)
);

CREATE INDEX idx_bre_tags_staging_session_id ON bre_tags_staging(session_id);

COMMENT ON TABLE bre_tags_staging IS 'Stores unique staged tag values per session';
COMMENT ON COLUMN bre_tags_staging.session_id IS 'Session identifier for staging isolation';
COMMENT ON COLUMN bre_tags_staging.name IS 'Tag name (unique per session)';

-- =============================================================================
-- 2. bre_tag_map_staging: Maps staged tags to file IDs per session
-- =============================================================================
CREATE TABLE IF NOT EXISTS bre_tag_map_staging (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(128) NOT NULL,
    tag_id INTEGER NOT NULL REFERENCES bre_tags_staging(id) ON DELETE CASCADE,
    file_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bre_tag_map_staging_session_id ON bre_tag_map_staging(session_id);
CREATE INDEX idx_bre_tag_map_staging_file_id ON bre_tag_map_staging(file_id);
CREATE INDEX idx_bre_tag_map_staging_tag_id ON bre_tag_map_staging(tag_id);

COMMENT ON TABLE bre_tag_map_staging IS 'Maps staged tags to file IDs per session';
COMMENT ON COLUMN bre_tag_map_staging.session_id IS 'Session identifier for staging isolation';
COMMENT ON COLUMN bre_tag_map_staging.tag_id IS 'FK to bre_tags_staging.id';
COMMENT ON COLUMN bre_tag_map_staging.file_id IS 'File identifier (matches Nextcloud file IDs)';

-- =============================================================================
-- 3. bre_descriptions_staging: Staged descriptions per session
-- =============================================================================
CREATE TABLE IF NOT EXISTS bre_descriptions_staging (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(128) NOT NULL,
    file_id VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bre_descriptions_staging_session_id ON bre_descriptions_staging(session_id);
CREATE INDEX idx_bre_descriptions_staging_file_id ON bre_descriptions_staging(file_id);

COMMENT ON TABLE bre_descriptions_staging IS 'Staged descriptions per session';
COMMENT ON COLUMN bre_descriptions_staging.session_id IS 'Session identifier for staging isolation';
COMMENT ON COLUMN bre_descriptions_staging.file_id IS 'File identifier';
COMMENT ON COLUMN bre_descriptions_staging.description IS 'The AI-generated description text';

-- =============================================================================
-- 4. bre_descriptions: Production descriptions (max 3 per file with pinning)
-- =============================================================================
CREATE TABLE IF NOT EXISTS bre_descriptions (
    id SERIAL PRIMARY KEY,
    file_id VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pinned BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_bre_descriptions_file_id ON bre_descriptions(file_id);
CREATE UNIQUE INDEX idx_bre_descriptions_file_pinned_unique ON bre_descriptions(file_id, pinned) WHERE pinned = TRUE;

COMMENT ON TABLE bre_descriptions IS 'Production descriptions (max 3 per file, one pinned)';
COMMENT ON COLUMN bre_descriptions.file_id IS 'File identifier';
COMMENT ON COLUMN bre_descriptions.description IS 'The finalized description text';
COMMENT ON COLUMN bre_descriptions.pinned IS 'If TRUE, description is protected from auto-deletion';

-- =============================================================================
-- Function to auto-update updated_at timestamp
-- =============================================================================
CREATE OR REPLACE FUNCTION update_bre_descriptions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_bre_descriptions_updated_at_trigger ON bre_descriptions;
CREATE TRIGGER update_bre_descriptions_updated_at_trigger
    BEFORE UPDATE ON bre_descriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_bre_descriptions_updated_at();

-- =============================================================================
-- Trigger to enforce max 3 non-pinned descriptions per file
-- =============================================================================
CREATE OR REPLACE FUNCTION enforce_max_descriptions()
RETURNS TRIGGER AS $$
DECLARE
    oldest_id INTEGER;
BEGIN
    -- Only enforce for non-pinned descriptions
    IF NEW.pinned = FALSE THEN
        -- Check if there are already 3+ non-pinned descriptions for this file
        IF (SELECT COUNT(*) FROM bre_descriptions WHERE file_id = NEW.file_id AND pinned = FALSE) >= 3 THEN
            -- Find and delete the oldest non-pinned description
            SELECT id INTO oldest_id
            FROM bre_descriptions
            WHERE file_id = NEW.file_id AND pinned = FALSE
            ORDER BY created_at ASC
            LIMIT 1;
            
            DELETE FROM bre_descriptions WHERE id = oldest_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_enforce_max_descriptions ON bre_descriptions;
CREATE TRIGGER trigger_enforce_max_descriptions
    BEFORE INSERT ON bre_descriptions
    FOR EACH ROW
    EXECUTE FUNCTION enforce_max_descriptions();

COMMIT;
