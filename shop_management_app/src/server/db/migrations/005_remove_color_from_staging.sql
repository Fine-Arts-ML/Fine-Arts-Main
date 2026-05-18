-- Migration: 005_remove_color_from_staging
-- Description: Remove color column from bre_tags_staging table
-- Purpose: Color is managed by Nextcloud in oc_systemtag; staging should not track it

BEGIN;

ALTER TABLE bre_tags_staging DROP COLUMN IF EXISTS color;

COMMIT;
