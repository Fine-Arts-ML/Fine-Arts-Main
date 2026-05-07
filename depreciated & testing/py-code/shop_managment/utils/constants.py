"""
Configuration constants for the Shop Management app.
"""

import os

# Application version (auto-injected during Docker build via VERSION file)
APP_VERSION = os.getenv("APP_VERSION", "1.0.1")

# Pagination and display settings
PAGE_SIZES = {
    "small": 10,
    "medium": 20,
    "large": 50,
    "xlarge": 100,
}

# Layout settings
FILES_PER_ROW = 3
IMAGES_PER_ROW = 2
BATCH_SIZES = [10, 20, 50, 100]

# Hash types for reverse image search
HASH_TYPES = ["WHASH", "AHASH", "PHASH"]

# Default database host
DEFAULT_DB_HOST = "192.168.0.150"

# Image resize dimensions
IMAGE_RESIZE_1080 = (1080, 1080)
IMAGE_RESIZE_540 = (540, 540)
IMAGE_PREVIEW_200 = (200, 200)
IMAGE_PREVIEW_100 = (100, 100)
