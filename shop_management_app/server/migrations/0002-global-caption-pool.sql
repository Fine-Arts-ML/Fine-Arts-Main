-- Migration: 0002-global-caption-pool.sql
-- Date: 2026-07-10
-- Description: Create global caption pool, add main caption support, convert junction table

BEGIN;

-- Step 1: Create the global caption pool
CREATE TABLE IF NOT EXISTS bre_captions (
  caption_id   SERIAL PRIMARY KEY,
  caption      TEXT NOT NULL,
  created_by   INTEGER NOT NULL REFERENCES bre_user_accounts(id),
  created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Unique index to prevent duplicate caption text
CREATE UNIQUE INDEX IF NOT EXISTS idx_bre_captions_unique_caption ON bre_captions (caption);

-- Step 2: Add caption_id column to junction table (idempotent — skip if exists)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'bre_gallery_image_captions' AND column_name = 'caption_id'
  ) THEN
    ALTER TABLE bre_gallery_image_captions
      ADD COLUMN caption_id INTEGER REFERENCES bre_captions(caption_id);
  END IF;
END $$;

-- Step 3: Add is_main column to junction table (idempotent — skip if exists)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'bre_gallery_image_captions' AND column_name = 'is_main'
  ) THEN
    ALTER TABLE bre_gallery_image_captions
      ADD COLUMN is_main BOOLEAN NOT NULL DEFAULT false;
  END IF;
END $$;

-- Step 4: Backfill — create global captions from existing caption texts
-- Skip if bre_captions already populated
INSERT INTO bre_captions (caption, created_by, created_at)
SELECT DISTINCT gc.caption, gc.created_by, gc.created_at
FROM bre_gallery_image_captions gc
WHERE gc.caption IS NOT NULL
  AND gc.caption_id IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM bre_captions bc WHERE bc.caption = gc.caption
  );

-- Step 5: Link existing gallery_image_captions to their global caption counterparts
-- Only link rows where caption_id is still NULL
DO $$
BEGIN
  -- Check if the table has an 'id' column (primary key)
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'bre_gallery_image_captions' AND column_name = 'id'
  ) THEN
    -- Table has 'id' column — use it for the CTE
    UPDATE bre_gallery_image_captions gc
    SET 
      caption_id = bc.caption_id,
      is_main = CASE WHEN r.rn = 1 THEN true ELSE false END
    FROM (
      SELECT 
        id,
        ROW_NUMBER() OVER (PARTITION BY gallery_image_id ORDER BY created_at) AS rn
      FROM bre_gallery_image_captions
      WHERE caption IS NOT NULL AND caption_id IS NULL
    ) r
    INNER JOIN bre_captions bc ON bc.caption = gc.caption AND bc.created_by = gc.created_by
    WHERE gc.id = r.id AND gc.caption_id IS NULL;
  ELSE
    -- Table has no 'id' column — link all unmatched rows directly
    UPDATE bre_gallery_image_captions gc
    SET 
      caption_id = bc.caption_id,
      is_main = false
    FROM bre_captions bc
    WHERE gc.caption = bc.caption
      AND gc.created_by = bc.created_by
      AND gc.caption_id IS NULL;
  END IF;
END $$;

-- Step 6: Add unique constraint to junction table (idempotent)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'uq_gallery_image_caption'
      AND table_name = 'bre_gallery_image_captions'
  ) THEN
    ALTER TABLE bre_gallery_image_captions
      ADD CONSTRAINT uq_gallery_image_caption UNIQUE (gallery_image_id, caption_id);
  END IF;
END $$;

-- Step 7: Create indexes for performance (idempotent)
CREATE INDEX IF NOT EXISTS idx_gallery_image_captions_gallery_image_id
  ON bre_gallery_image_captions (gallery_image_id);
CREATE INDEX IF NOT EXISTS idx_gallery_image_captions_caption_id
  ON bre_gallery_image_captions (caption_id);

-- Step 8: Add orphan cleanup function
CREATE OR REPLACE FUNCTION cleanup_orphaned_captions()
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  -- Delete captions that have no links in bre_gallery_image_captions
  DELETE FROM bre_captions bc
  WHERE NOT EXISTS (
    SELECT 1 FROM bre_gallery_image_captions gc
    WHERE gc.caption_id = bc.caption_id
  );
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMIT;
