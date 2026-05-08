#!/bin/bash
# =============================================================================
# Build script for Shop Management Docker images
# =============================================================================
# This script builds all Docker images required for the Shop Management
# application including:
#   - shop-management-app (Nuxt.js frontend/backend)
#   - shop-management-rag-search (Python RAG search service)
#   - shop-management-hash-calc (Python hash calculation service)
#
# Usage: ./build.sh [option]
#   ./build.sh          - Build all images (default)
#   ./build.sh app      - Build only the main app
#   ./build.sh rag      - Build only the RAG search service
#   ./build.sh hash     - Build only the hash calculation service
#   ./build.sh --no-cache - Build all images without cache
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Image names
APP_IMAGE="shop-management-app:latest"
RAG_IMAGE="shop-management-rag-search:latest"
HASH_IMAGE="shop-management-hash-calc:latest"

# Script directory (where build.sh is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Shop Management Docker Build Script${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running or you don't have permission to use it.${NC}"
    echo "Please start Docker Desktop or check your permissions."
    exit 1
fi

# Build function
build_app() {
    echo -e "${YELLOW}Building main application image...${NC}"
    echo -e "${YELLOW}Image: ${APP_IMAGE}${NC}"
    cd "$SCRIPT_DIR"
    docker build -t "$APP_IMAGE" -f Dockerfile . 2>&1
    echo -e "${GREEN}Main application image built successfully.${NC}"
    echo ""
}

build_rag() {
    echo -e "${YELLOW}Building RAG search service image...${NC}"
    echo -e "${YELLOW}Image: ${RAG_IMAGE}${NC}"
    cd "$SCRIPT_DIR"
    docker build -t "$RAG_IMAGE" -f src/py-code/rag_search/Dockerfile src/py-code/rag_search 2>&1
    echo -e "${GREEN}RAG search service image built successfully.${NC}"
    echo ""
}

build_hash() {
    echo -e "${YELLOW}Building hash calculation service image...${NC}"
    echo -e "${YELLOW}Image: ${HASH_IMAGE}${NC}"
    cd "$SCRIPT_DIR"
    docker build -t "$HASH_IMAGE" -f src/py-code/hash_calc/Dockerfile src/py-code/hash_calc 2>&1
    echo -e "${GREEN}Hash calculation service image built successfully.${NC}"
    echo ""
}

# Parse arguments
BUILD_ALL=false
BUILD_APP=false
BUILD_RAG=false
BUILD_HASH=false
NO_CACHE=""

for arg in "$@"; do
    case $arg in
        --no-cache)
            NO_CACHE="--no-cache"
            ;;
        app)
            BUILD_APP=true
            ;;
        rag)
            BUILD_RAG=true
            ;;
        hash)
            BUILD_HASH=true
            ;;
        *)
            echo -e "${RED}Unknown argument: $arg${NC}"
            echo "Usage: $0 [app|rag|hash|--no-cache]"
            exit 1
            ;;
    esac
done

# Default: build all if no specific service requested
if [ "$BUILD_ALL" = false ] && [ "$BUILD_APP" = false ] && [ "$BUILD_RAG" = false ] && [ "$BUILD_HASH" = false ]; then
    BUILD_ALL=true
fi

# Build images
if [ "$BUILD_ALL" = true ] || [ "$BUILD_APP" = true ]; then
    build_app
fi

if [ "$BUILD_ALL" = true ] || [ "$BUILD_RAG" = true ]; then
    build_rag
fi

if [ "$BUILD_ALL" = true ] || [ "$BUILD_HASH" = true ]; then
    build_hash
fi

# List all images
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Built Images${NC}"
echo -e "${BLUE}============================================${NC}"
docker images | grep -E "SHOP-MANAGEMENT|shop-management" | awk '{printf "  %-40s %s\n", $1":"$2, $3}'
echo ""
echo -e "${GREEN}Build complete!${NC}"
echo ""
echo -e "Next steps:"
echo -e "  ${YELLOW}1.${NC} Export images:    ./export-images.sh"
echo -e "  ${YELLOW}2.${NC} Transfer to server (see DEPLOY.md)"
echo -e "  ${YELLOW}3.${NC} Deploy on server: See DEPLOY.md for instructions"
