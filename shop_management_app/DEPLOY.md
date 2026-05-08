# Shop Management - Docker Deployment Guide

This guide walks you through deploying the Shop Management application on a remote server using Docker.

## Architecture

The application consists of three services:

| Service | Port | Description |
|---------|------|-------------|
| `shop-management-app` | 3000 | Nuxt.js full-stack application (UI + API) |
| `shop-management-rag-search` | 8079 | Python RAG search service (semantic image search) |
| `shop-management-hash-calc` | 8078 | Python hash calculation service (reverse image search) |

## Prerequisites

- Docker and Docker Compose v2+ installed on your remote server
- PostgreSQL database accessible from the server
- Nextcloud instance accessible from the server
- At least 2-4 GB disk space for models and indexes

## Quick Start

### Step 1: Build Images Locally

On your development machine, navigate to the `shop_management_app` directory:

```bash
cd shop_management_app

# Build all images
./build.sh

# Or build specific services
./build.sh app    # Main application only
./build.sh rag    # RAG search service only
./build.sh hash   # Hash calculation service only
```

### Step 2: Export Images

```bash
./export-images.sh
```

This creates a timestamped directory (e.g., `docker-images-backup/shop-management-20260508_134500/`) containing all images as `.tar` files.

### Step 3: Transfer to Remote Server

Choose one of these methods:

**Option A: Using scp**
```bash
scp -r docker-images-backup/shop-management-20260508_134500/ user@your-server:/opt/shop-management/images/
```

**Option B: Using rsync**
```bash
rsync -avz docker-images-backup/shop-management-20260508_134500/ user@your-server:/opt/shop-management/images/
```

**Option C: Using tar over SSH (no intermediate storage)**
```bash
tar -czf - docker-images-backup/shop-management-20260508_134500/ | \
  ssh user@your-server 'tar -xzf - -C /opt/shop-management/images/'
```

### Step 4: Import on Remote Server

SSH into your remote server and navigate to the deployment directory:

```bash
# Import the images
./import-images.sh /opt/shop-management/images/shop-management-20260508_134500

# Verify images are loaded
docker images | grep shop-management
```

Expected output:
```
shop-management-app:latest                    <image-id>
shop-management-rag-search:latest             <image-id>
shop-management-hash-calc:latest              <image-id>
```

### Step 5: Configure Environment

Create a `.env` file in the deployment directory:

```bash
cd /opt/shop-management

cat > .env << EOF
# Database Configuration
DB_HOST=your-db-host
DB_PORT=5432
DB_NAME=shop_management
DB_USER=postgres
DB_PASSWORD=your-db-password

# Nextcloud Configuration
NC_HOST=your-nextcloud-host
NC_ACC=your-nextcloud-user
NC_PASS=your-nextcloud-password

# RAG Model (optional, default: qwen3-0.6b)
DEFAULT_MODEL=qwen3-0.6b

# Cloudflare Tunnel Token (optional, remove tunnel service if not used)
# CLOUDFLARE_TOKEN=your-token-here
EOF
```

### Step 6: Start Services

```bash
# Create necessary directories (for model persistence)
mkdir -p rag-models tfidf-index

# Start all services
docker compose -f docker-compose.deploy.yml up -d

# Check status
docker compose -f docker-compose.deploy.yml ps
```

### Step 7: Verify Deployment

```bash
# Check app health
curl http://localhost:3000/

# Check RAG service health
curl http://localhost:8079/api/v1/rag/health

# Check hash service health
curl http://localhost:8078/health
```

## Management Commands

### View Logs

```bash
# All services
docker compose -f docker-compose.deploy.yml logs -f

# Specific service
docker compose -f docker-compose.deploy.yml logs -f app
docker compose -f docker-compose.deploy.yml logs -f rag-search
docker compose -f docker-compose.deploy.yml logs -f hash-calc
```

### Stop Services

```bash
docker compose -f docker-compose.deploy.yml down
```

### Restart Services

```bash
docker compose -f docker-compose.deploy.yml restart
```

### Update Images

To update, rebuild locally, export, transfer, import, and restart:

```bash
# On your local machine
./build.sh
./export-images.sh /tmp/shop-management-export

# Transfer (see Step 3)

# On remote server
./import-images.sh /tmp/shop-management-export
docker compose -f docker-compose.deploy.yml down
docker compose -f docker-compose.deploy.yml up -d
```

## Cloudflare Tunnel (Optional)

If you want to expose the app securely without opening ports:

1. Create a Cloudflare Tunnel: https://one.dash.cloudflare.com/
2. Add the tunnel token to your `.env` file
3. The `tunnel` service will automatically connect
4. Access your app via the tunnel URL

## Troubleshooting

### Images not found

```bash
# List all images
docker images | grep shop-management

# If images are missing, re-import
./import-images.sh /path/to/export-directory
```

### Database connection errors

```bash
# Check if the app can reach the database
docker compose -f docker-compose.deploy.yml exec app ping $DB_HOST

# Check environment variables
docker compose -f docker-compose.deploy.yml exec app env | grep DB_
```

### RAG service not responding

```bash
# Check RAG service logs
docker compose -f docker-compose.deploy.yml logs rag-search

# The first startup may take 60+ seconds to download the model
# Check health:
curl http://localhost:8079/api/v1/rag/health
```

### High disk usage

The RAG models can take significant space. Check usage:

```bash
du -sh rag-models tfidf-index
```

## Directory Structure on Server

```
/opt/shop-management/
├── .env                          # Environment configuration
├── docker-compose.deploy.yml     # Docker Compose configuration
├── import-images.sh              # Image import script
├── rag-models/                   # RAG models (persistent volume)
│   └── Models/
├── tfidf-index/                  # TF-IDF index (persistent volume)
│   └── tfidf-index/
└── images/                       # Exported images
    └── shop-management-YYYYMMDD_HHMMSS/
        ├── shop-management-app-latest.tar
        ├── shop-management-rag-search-latest.tar
        ├── shop-management-hash-calc-latest.tar
        └── MANIFEST.txt
```
