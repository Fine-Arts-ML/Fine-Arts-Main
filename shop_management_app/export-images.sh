#!/bin/bash
# =============================================================================
# Export Docker images for transfer to remote server
# =============================================================================
# This script exports all Docker images as tar files that can be
# transferred to a remote server using scp, rsync, or other methods.
#
# Usage: ./export-images.sh [output_directory]
#   ./export-images.sh              - Export to ./docker-images-backup/
#   ./export-images.sh /tmp/images  - Export to /tmp/images/
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Image names
IMAGES=(
    "shop-management-app:latest"
    "shop-management-rag-search:latest"
    "shop-management-hash-calc:latest"
)

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Output directory (default: docker-images-backup in script directory)
OUTPUT_DIR="${SCRIPT_DIR}/docker-images-backup"
if [ $# -ge 1 ]; then
    OUTPUT_DIR="$1"
fi

# Version tag for this export (for naming)
VERSION_TAG=$(date +%Y%m%d_%H%M%S)
EXPORT_DIR="${OUTPUT_DIR}/shop-management-${VERSION_TAG}"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Docker Image Export Script${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running or you don't have permission to use it.${NC}"
    exit 1
fi

# Create export directory
mkdir -p "$EXPORT_DIR"
echo -e "${YELLOW}Export directory: ${EXPORT_DIR}${NC}"
echo ""

# Check if images exist and export them
exported_count=0
failed_count=0

for image in "${IMAGES[@]}"; do
    image_name=$(echo "$image" | cut -d: -f1)
    tag=$(echo "$image" | cut -d: -f2)
    filename="${image_name//\//-}-${tag}.tar"
    
    echo -e "${YELLOW}Checking image: ${image}${NC}"
    
    # Check if image exists
    if ! docker image inspect "$image" > /dev/null 2>&1; then
        echo -e "${RED}  Error: Image '${image}' not found.${NC}"
        echo -e "${RED}  Please build it first: ./build.sh${NC}"
        ((failed_count++)) || true
        continue
    fi
    
    # Get image size
    size=$(docker image inspect "$image" --format='{{.Size}}' | awk '{printf "%.1f MB", $1/1024/1024}')
    
    echo -e "${YELLOW}  Exporting: ${image} (${size})${NC}"
    
    # Export the image
    docker save -o "${EXPORT_DIR}/${filename}" "$image" 2>&1
    
    if [ $? -eq 0 ]; then
        # Get actual file size
        actual_size=$(du -h "${EXPORT_DIR}/${filename}" | cut -f1)
        echo -e "${GREEN}  Exported: ${filename} (${actual_size})${NC}"
        ((exported_count++)) || true
    else
        echo -e "${RED}  Failed to export ${image}${NC}"
        ((failed_count++)) || true
    fi
done

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Export Summary${NC}"
echo -e "${BLUE}============================================${NC}"
echo -e "  Exported: ${GREEN}${exported_count}${NC}"
if [ $failed_count -gt 0 ]; then
    echo -e "  Failed:   ${RED}${failed_count}${NC}"
fi
echo -e "  Location: ${YELLOW}${EXPORT_DIR}${NC}"
echo ""

# Create a manifest file
cat > "${EXPORT_DIR}/MANIFEST.txt" << EOF
Shop Management Docker Images Export
=====================================
Export Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Hostname: $(hostname)

Images Exported:
$(for image in "${IMAGES[@]}"; do
    if docker image inspect "$image" > /dev/null 2>&1; then
        size=$(docker image inspect "$image" --format='{{.Size}}')
        echo "  - ${image} ($(echo "$size" | awk '{printf "%.1f MB", $1/1024/1024}'))"
    fi
done)

Deployment Instructions:
1. Transfer this directory to your remote server
2. On the remote server, run: ./import-images.sh <this_directory>
3. Then run: docker compose -f docker-compose.deploy.yml up -d

Notes:
- Ensure .env file is copied to the deployment directory
- PostgreSQL must be running and accessible
- At least 2GB disk space needed for models and indexes
EOF

echo -e "${GREEN}Manifest created: ${EXPORT_DIR}/MANIFEST.txt${NC}"
echo ""

# Calculate total size
total_size=$(du -sh "$EXPORT_DIR" | cut -f1)
echo -e "${GREEN}Total export size: ${total_size}${NC}"
echo ""

# Show transfer options
echo -e "${BLUE}Transfer options:${NC}"
echo ""
echo -e "  ${YELLOW}Option 1: Using scp${NC}"
echo "    scp -r ${EXPORT_DIR}/ user@your-server:/path/to/deployment/"
echo ""
echo -e "  ${YELLOW}Option 2: Using rsync${NC}"
echo "    rsync -avz ${EXPORT_DIR}/ user@your-server:/path/to/deployment/"
echo ""
echo -e "  ${YELLOW}Option 3: Using tar over ssh (no intermediate storage)${NC}"
echo "    tar -czf - ${EXPORT_DIR} | ssh user@your-server 'tar -xzf - -C /path/to/deployment/'"
echo ""
echo -e "${GREEN}Export complete!${NC}"
