# Shop Management - Docker Deployment Guide

## Prerequisites

- Docker Engine 24+
- Docker Compose v2.23+
- At least 2GB RAM available for the containers

## Environment Variables

Create a `.env` file in the `typescript/shop_management` directory with the following variables:

### Database Configuration

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DB_HOST` | Yes | Hostname or IP of the PostgreSQL server | `your_db_host` |
| `DB_PORT` | Yes | PostgreSQL port | `5432` |
| `DB_NAME` | Yes | Database name | `your_db_name` |
| `DB_USER` | Yes | Database username | `your_db_user` |
| `DB_PASSWORD` | Yes | Database password | `your_db_password` |

### Nextcloud Configuration

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `NC_ACC` | Yes | Nextcloud username | `your_nextcloud_user` |
| `NC_PASS` | Yes | Nextcloud password or app password | `your_nextcloud_password` |
| `NC_HOST` | Optional | Nextcloud host (defaults to `your_nextcloud_host`) | `your_nextcloud_host` |

### RAG Search Configuration

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DEFAULT_MODEL` | Optional | Default model to use for RAG search (defaults to `qwen3-0.6b`) | `qwen3-0.6b` |

### Full `.env` Example

```env
# Database Configuration
DB_HOST=your_db_host
DB_PORT=5432
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password

# Nextcloud Configuration (for preview images)
NC_ACC=your_nextcloud_user
NC_PASS=your_nextcloud_password
NC_HOST=your_nextcloud_host

# RAG Search Configuration
DEFAULT_MODEL=qwen3-0.6b
```

## Deployment Steps

### 1. Build Images

```bash
cd typescript/shop_management
docker compose build
```

This builds two images:
- `shop_management-app`: The Nuxt.js frontend/backend application
- `shop_management-rag-search`: The Python RAG search service

### 2. Start Containers

```bash
docker compose up -d
```

### 3. Verify Deployment

Check container status:
```bash
docker compose ps
```

Expected output:
```
NAME                           STATUS
shop_management-app-1          Up (healthy)
shop_management-rag-search-1   Up (healthy)
```

Test the application:
```bash
# Application (redirects to /shops)
curl http://localhost:3000/

# RAG Search Health Check
curl http://localhost:8079/api/v1/rag/health
```

### 4. View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f app
docker compose logs -f rag-search
```

### 5. Stop Containers

```bash
docker compose down
```

To remove volumes (this will delete stored models and indexes):
```bash
docker compose down -v
```

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| app | 3000 | Nuxt.js application |
| rag-search | 8079 | Python RAG search API |

## Docker Compose Services

### `app`
The main Nuxt.js application that provides:
- Web UI for shop management
- File browsing and preview
- Account management
- API endpoints for frontend

### `rag-search`
Python FastAPI service for RAG (Retrieval-Augmented Generation) search:
- Semantic search over file metadata
- TF-IDF indexing
- Model caching

### Persistent Volumes

| Volume | Purpose |
|--------|---------|
| `rag-models` | Stores downloaded ML models |
| `rag-index` | Stores TF-IDF index data |

## Troubleshooting

### Containers restarting repeatedly

Check logs for errors:
```bash
docker compose logs app
docker compose logs rag-search
```

Common issues:
- Missing or incorrect `.env` variables
- Database connection failures (check `DB_HOST` is reachable)

### Rebuild after changes

```bash
docker compose down
docker compose build
docker compose up -d
```

### Access container shells

```bash
docker exec -it shop_management-app-1 sh
docker exec -it shop_management-rag-search-1 sh
```
