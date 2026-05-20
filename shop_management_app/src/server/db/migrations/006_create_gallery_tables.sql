-- Migration: 006_create_gallery_tables
-- Description: Create gallery management tables
-- Purpose: Enable admin/gallery management and guest gallery viewing
-- Note: Uses oc_filecache.fileid (bigint PK) as the canonical file identifier

BEGIN;

-- 1. Gallery Master Table
CREATE TABLE bre_galleries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by INTEGER NOT NULL REFERENCES bre_user_accounts(id),
    updated_by INTEGER REFERENCES bre_user_accounts(id),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bre_galleries_created_by ON bre_galleries(created_by);
CREATE INDEX idx_bre_galleries_is_active ON bre_galleries(is_active);

-- 2. Gallery Access Table (maps guests to galleries)
CREATE TABLE bre_gallery_access (
    gallery_id INTEGER NOT NULL REFERENCES bre_galleries(id) ON DELETE CASCADE,
    guest_user_id INTEGER NOT NULL REFERENCES bre_user_accounts(id),
    granted_by INTEGER NOT NULL REFERENCES bre_user_accounts(id),
    granted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (gallery_id, guest_user_id)
);

CREATE INDEX idx_bre_gallery_access_guest ON bre_gallery_access(guest_user_id);
CREATE INDEX idx_bre_gallery_access_gallery ON bre_gallery_access(gallery_id);

-- 3. Gallery-Image Mapping Table
-- References oc_filecache.fileid (bigint PK) as the canonical file identifier
CREATE TABLE bre_gallery_images (
    id SERIAL PRIMARY KEY,
    gallery_id INTEGER NOT NULL REFERENCES bre_galleries(id) ON DELETE CASCADE,
    file_id BIGINT NOT NULL REFERENCES oc_filecache(fileid),
    display_order INTEGER NOT NULL DEFAULT 0,
    caption TEXT,
    added_by INTEGER NOT NULL REFERENCES bre_user_accounts(id),
    added_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (gallery_id, file_id)
);

CREATE INDEX idx_bre_gallery_images_gallery ON bre_gallery_images(gallery_id);
CREATE INDEX idx_bre_gallery_images_order ON bre_gallery_images(gallery_id, display_order);
CREATE INDEX idx_bre_gallery_images_file ON bre_gallery_images(file_id);

-- Auto-update trigger for updated_at on bre_galleries
CREATE TRIGGER update_bre_galleries_updated_at
    BEFORE UPDATE ON bre_galleries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to update allowed_gallery_ids JSONB cache on bre_user_accounts
CREATE OR REPLACE FUNCTION sync_gallery_access_cache()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the cache for the guest user
    UPDATE bre_user_accounts
    SET allowed_gallery_ids = (
        SELECT COALESCE(jsonb_agg(ga.gallery_id::text), '[]'::jsonb)
        FROM bre_gallery_access ga
        WHERE ga.guest_user_id = bre_user_accounts.id
    )
    WHERE id = NEW.guest_user_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sync_gallery_access_cache
    AFTER INSERT OR UPDATE ON bre_gallery_access
    FOR EACH ROW
    EXECUTE FUNCTION sync_gallery_access_cache();

-- Cleanup trigger to remove from cache on delete
CREATE OR REPLACE FUNCTION sync_gallery_access_cache_remove()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE bre_user_accounts
    SET allowed_gallery_ids = (
        SELECT COALESCE(jsonb_agg(ga.gallery_id::text), '[]'::jsonb)
        FROM bre_gallery_access ga
        WHERE ga.guest_user_id = OLD.guest_user_id
    )
    WHERE id = OLD.guest_user_id;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sync_gallery_access_cache_remove
    AFTER DELETE ON bre_gallery_access
    FOR EACH ROW
    EXECUTE FUNCTION sync_gallery_access_cache_remove();

COMMIT;
