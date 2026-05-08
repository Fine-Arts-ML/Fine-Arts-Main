#!/bin/bash
# =============================================================================
# Import Docker images on remote server
# =============================================================================
# This script imports Docker images that were exported from the build machine.
# Run this on your remote server after transferring the exported images.
#
# Usage: ./import-images.sh <export_directory>
#   ./import-images.sh /path/to/docker-images-backup/shop-management-20240101_120000
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Docker Image Import Script${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: Please provide the export directory path.${NC}"
    echo ""
    echo "Usage: $0 <export_directory>"
    echo "Example: $0 /opt/docker-images/shop-management-20240101_120000"
    exit 1
fi

EXPORT_DIR="$1"

# Check if directory exists
if [ ! -d "$EXPORT_DIR" ]; then
    echo -e "${RED}Error: Directory '${EXPORT_DIR}' does not exist.${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running or you don't have permission to use it.${NC}"
    exit 1
fi

echo -e "${YELLOW}Import directory: ${EXPORT_DIR}${NC}"
echo ""

# Find all tar files
tar_files=($(find "$EXPORT_DIR" -name "*.tar" -type f | sort))

if [ ${#tar_files[@]} -eq 0 ]; then
    echo -e "${RED}Error: No .tar files found in '${EXPORT_DIR}'.${NC}"
    exit 1
fi

echo -e "${BLUE}Found ${#tar_files[@]} image(s) to import:${NC}"
echo ""

imported_count=0
failed_count=0

for tar_file in "${tar_files[@]}"; do
    filename=$(basename "$tar_file")
    echo -e "${YELLOW}Importing: ${filename}${NC}"
    
    # Get file size
    file_size=$(du -h "$tar_file" | cut -f1)
    echo -e "  Size: ${file_size}"
    
    # Import the image
    if docker load -i "$tar_file" 2>&1; then
        echo -e "  ${GREEN}Imported successfully${NC}"
        ((imported_count++)) || true
    else
        echo -e "  ${RED}Failed to import${NC}"
        ((failed_count++)) || true
    fi
    echo ""
done

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Import Summary${NC}"
echo -e "${BLUE}============================================${NC}"
echo -e "  Imported: ${GREEN}${imported_count}${NC}"
if [ $failed_count -gt 0 ]; then
    echo -e "  Failed:   ${RED}${failed_count}${NC}"
fi
echo ""

# List imported images
echo -e "${BLUE}Imported images:${NC}"
docker images | grep -E "shop-management" | awk '{printf "  %-40s %s\n", $1":"$2, $3}'
echo ""

# Show manifest if available
if [ -f "${EXPORT_DIR}/MANIFEST.txt" ]; then
    echo -e "${BLUE}Manifest:${NC}"
    cat "${EXPORT_DIR}/MANIFEST.txt"
    echo ""
fi

echo -e "${GREEN}Import complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Copy your .env file to the deployment directory"
echo -e "  2. Create necessary directories for volumes:"
echo -e "     mkdir -p ./rag-models ./tfidf-index"
echo -e "  3. Start the services:"
echo -e "     docker compose -f docker-compose.deploy.yml up -d"
echo -e "  4. Check service status:"
echo -e "     docker compose -f docker-compose.deploy.yml ps"
