# Deployment Guide

Transfer and run the shop management app on a new server using pre-built Docker images.

## Prerequisites

- Docker Engine 20.10+ with `docker compose` v2 plugin
- Minimum 4GB RAM (RAG service requires ~2GB)
- PostgreSQL database server (or use included docker-compose with DB)

## Quick Start

### 1. Transfer Files to Target Server

```bash
# On source server, create a tarball of the export files
cd typescript/shop_management
tar czf shop_management-deploy.tar.gz \
  shop_management-app-latest.tar.gz \
  shop_management-rag-search-latest.tar.gz \
  docker-compose.deploy.yml \
  .env.example \
  README.md \
  DEPLOY.md

# Transfer to target server
scp shop_management-deploy.tar.gz user@target-server:/opt/shop_management/
```

### 2. Setup on Target Server

```bash
# SSH into target server and extract
ssh user@target-server
sudo mkdir -p /opt/shop_management
sudo tar xzf shop_management-deploy.tar.gz -C /opt/shop_management/
cd /opt/shop_management

# Load Docker images
sudo docker load < shop_management-app-latest.tar.gz
sudo docker load < shop_management-rag-search-latest.tar.gz

# Verify images loaded
sudo docker images | grep shop_management
```

Expected output:
```
shop_management-app:latest
shop_management-rag-search:latest
```

### 3. Configure Environment

```bash
# Copy and edit the environment file
cp .env.example .env
nano .env
```

Required variables in `.env`:
```env
# Database (change if using external DB)
DB_HOST=postgres
DB_PORT=5432
DB_NAME=shop_management
DB_USER=postgres
DB_PASSWORD=your_secure_password

# Nextcloud (for image previews)
NC_HOST=https://your-nextcloud.com
NC_ACC=your_nextcloud_user
NC_PASS=your_nextcloud_app_password

# RAG settings
DEFAULT_MODEL=qwen3-0.6b
```

### 4. Prepare Model Directory

```bash
# Copy RAG models if you have them
# From original server:
scp -r typescript/shop_management/src/rag-models user@target-server:/opt/shop_management/rag-models/

# Or download models after starting the service via the UI
mkdir -p rag-models
```

### 5. Start Services

```bash
# Using the deployment compose file
sudo docker compose -f docker-compose.deploy.yml up -d

# Check status
sudo docker compose -f docker-compose.deploy.yml ps
```

### 6. Verify Deployment

```bash
# Check app health
curl http://localhost:3000/

# Check RAG service health
curl http://localhost:8079/api/v1/rag/health
```

## Managing Services

```bash
# Start
sudo docker compose -f docker-compose.deploy.yml up -d

# Stop
sudo docker compose -f docker-compose.deploy.yml down

# View logs
sudo docker compose -f docker-compose.deploy.yml logs -f

# Restart specific service
sudo docker compose -f docker-compose.deploy.yml restart app
sudo docker compose -f docker-compose.deploy.yml restart rag-search

# Update environment
sudo docker compose -f docker-compose.deploy.yml down
# Edit .env
sudo docker compose -f docker-compose.deploy.yml up -d
```

## Troubleshooting

### App won't start
```bash
# Check app logs
sudo docker logs shop_management-app

# Common issue: Database not reachable
# Ensure DB_HOST is correct and database is accessible
```

### RAG service health check failing
```bash
# Check RAG logs
sudo docker logs shop_management-rag-search

# Models may need to be downloaded first
# Access /settings in the UI to download models
```

### Port already in use
```bash
# Check what's using port 3000
sudo lsof -i :3000

# Change port mapping in docker-compose.deploy.yml
# Change "3000:3000" to "XXXX:3000"
```

## Backup

```bash
# Backup database
sudo docker exec -t shop_management-db pg_dump -U postgres shop_management > backup.sql

# Backup models
tar czf models-backup.tar.gz rag-models/
```
