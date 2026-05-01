# RAG (Retrieval-Augmented Generation) Search - Technical Documentation

## Overview

The application includes a RAG-based semantic search feature that enables natural language search over files using TF-IDF weighted embeddings from sentence transformer models.

### Architecture Overview

```
User Query -> Vue Composable -> Nuxt API Route -> Python FastAPI Service -> PostgreSQL
     <-        <-               <-                 <-                        <-
```

1. User enters a natural language query in the UI
2. [`useRagSearch()`](src/composables/useRagSearch.ts) composable sends request to `/api/files/rag-search`
3. Nuxt API route proxies the request to the Python FastAPI RAG service
4. Python service encodes the query using a sentence transformer model
5. TF-IDF weighted embeddings are compared against pre-computed file embeddings
6. Top-k results are returned with similarity scores

---

## Python RAG Service (`src/py-code/rag_search/`)

The RAG service is a standalone FastAPI application that provides semantic search capabilities.

### Service Components

| Module | File | Purpose |
|--------|------|---------|
| Main App | [`main.py`](src/py-code/rag_search/main.py) | FastAPI application with API endpoints |
| Configuration | [`config.py`](src/py-code/rag_search/config.py) | RAG configuration (database, models, search settings) |
| Model Loader | [`model_loader.py`](src/py-code/rag_search/model_loader.py) | Manages loading, caching, and unloading of embedding models |
| TF-IDF Index | [`tfidf_index.py`](src/py-code/rag_search/tfidf_index.py) | TF-IDF vectorization and index persistence |
| Database | [`database.py`](src/py-code/rag_search/database.py) | Database connection and query handler |
| Search | [`search.py`](src/py-code/rag_search/search.py) | Core search logic using TF-IDF weighted embeddings |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/rag/search` | POST | Perform semantic search |
| `/api/v1/rag/models` | GET | List available models |
| `/api/v1/rag/models/current` | GET | Get current model |
| `/api/v1/rag/models/switch` | POST | Switch to a different model |
| `/api/v1/rag/models/download` | POST | Download a model |
| `/api/v1/rag/cache/config` | GET | Get cache configuration |
| `/api/v1/rag/cache/config` | POST | Update cache configuration |
| `/api/v1/rag/cache/evict` | POST | Evict unused models from cache |
| `/api/v1/rag/index/rebuild` | POST | Rebuild TF-IDF index |
| `/api/v1/rag/health` | GET | Health check |

### Search Request/Response

**Request:**
```json
{
  "query": "landscape painting with mountains",
  "top_k": 24,
  "preview_size": 540
}
```

**Response:**
```json
{
  "results": [
    {
      "file_id": 123,
      "filename": "mountain_view.jpg",
      "similarity": 0.8542,
      "preview_url": "/core/preview?fileId=123&{prevsize}",
      "tags": "landscape,mountain,nature"
    }
  ],
  "query_time_ms": 145.32
}
```

### Search Algorithm

1. **Query Encoding**: The user's query is encoded into a vector using the selected sentence transformer model
2. **Document Embeddings**: Pre-computed file embeddings are loaded from cache (saved as `.npy` files)
3. **Cosine Similarity**: The query embedding is compared against all document embeddings
4. **Top-k Selection**: The top-k most similar files are selected
5. **Metadata Fetching**: File metadata (name, preview URL, tags) is fetched from the database
6. **Result Building**: Results are assembled with similarity scores and preview URLs

### Model Management

The service supports multiple embedding models with caching:

| Model ID | Description | Parameters | Disk Size | RAM Usage | Load Time |
|----------|-------------|------------|-----------|-----------|-----------|
| `qwen3-0.6b` | Best accuracy, recommended for production | 600M | ~1.2GB | ~1.5GB | ~10 seconds |

**Model Caching:**
- Models are cached in memory using an LRU (Least Recently Used) strategy
- Maximum cached models is configurable via `MAX_CACHED_MODELS` environment variable (default: 1)
- Unused models are automatically evicted when cache is full
- Models are discovered dynamically from the `MODELS_DIR` directory

### TF-IDF Index

The TF-IDF index is built from file tags in the database:

1. **Tag Collection**: All system tags (`oc_systemtag`) and their file mappings (`oc_systemtag_object_mapping`) are loaded
2. **Document Building**: Tags are aggregated per file and sorted alphabetically
3. **Vectorization**: TF-IDF vectorizer is fitted on the document corpus
4. **Persistence**: Index is saved to disk as `.npz` (sparse matrix) + `.json` (metadata)

**Index Files:**
- `tfidf_matrix.npz` - Sparse TF-IDF matrix
- `tfidf_meta.json` - Vocabulary and file IDs
- `doc_embeddings.npy` - Pre-computed document embeddings
- `doc_embeddings_meta.json` - Embedding metadata

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `shop_management` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `postgres` |
| `MODELS_DIR` | Directory containing model files | `/py-code/Models` |
| `DEFAULT_MODEL` | Default model to use | `qwen3-0.6b` |
| `MAX_CACHED_MODELS` | Maximum models to cache in memory | `1` |
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `8079` |
| `INDEX_DIR` | Directory for TF-IDF index files | `/data/tfidf-index` |

### Running the RAG Service

```bash
cd typescript/shop_management/src/py-code
MODELS_DIR=/path/to/models DEFAULT_MODEL=qwen3-0.6b \
DB_HOST=192.168.0.150 DB_NAME=nextpsql DB_USER=nextuser DB_PASSWORD='password' \
HOST=0.0.0.0 PORT=8079 INDEX_DIR=/path/to/index \
PYTHONPATH=. .venv/bin/python -m rag_search.main
```

---

## Nuxt API Routes (Proxy Layer)

The Nuxt application provides proxy routes that forward requests to the Python RAG service:

| Nuxt Route | Python Endpoint | Description |
|------------|-----------------|-------------|
| `POST /api/files/rag-search` | `POST /api/v1/rag/search` | Semantic search |
| `GET /api/settings/rag-models` | `GET /api/v1/rag/models` | List models |
| `GET /api/settings/rag-cache-config` | `GET /api/v1/rag/cache/config` | Get cache config |
| `POST /api/settings/rag-cache-config` | `POST /api/v1/rag/cache/config` | Update cache config |
| `POST /api/settings/rag-cache/evict` | `POST /api/v1/rag/cache/evict` | Evict cache |
| `GET /api/settings/rag-model/current` | `GET /api/v1/rag/models/current` | Get current model |
| `POST /api/settings/rag-model` | `POST /api/v1/rag/models/switch` | Switch model |
| `POST /api/settings/rag-model/download` | `POST /api/v1/rag/models/download` | Download model |
| `POST /api/settings/rag-index/rebuild` | `POST /api/v1/rag/index/rebuild` | Rebuild index |

**Service URL Configuration:**
```typescript
const ragServiceUrl = process.env.RAG_SERVICE_URL || 'http://localhost:8079'
```

---

## Vue Composables

### useRagSearch (`src/composables/useRagSearch.ts`)

Provides semantic search functionality for the UI.

**State:**
| Property | Type | Description |
|----------|------|-------------|
| `results` | `SearchResult[]` | Search results |
| `isLoading` | `boolean` | Loading state |
| `error` | `string \| null` | Error message |
| `queryTimeMs` | `number` | Query execution time in milliseconds |

**Methods:**
| Method | Parameters | Description |
|--------|------------|-------------|
| `search` | `query: string, options?: UseRagSearchOptions` | Perform semantic search |
| `clearResults` | None | Clear search results |
| `getLastQuery` | None | Get the last search query |
| `getLastOptions` | None | Get the last search options |

**Search Options:**
```typescript
interface UseRagSearchOptions {
  top_k?: number      // Number of results (default: 24)
  previewSize?: number // Preview image size (default: 540)
}
```

**Usage Example:**
```vue
<script setup lang="ts">
import { useRagSearch, type SearchResult } from '~/composables/useRagSearch'
import { ref } from 'vue'

const { search, clearResults, state } = useRagSearch()
const ragResults = ref<SearchResult[]>([])

async function handleSearch(query: string) {
  const result = await search(query, { top_k: 12, previewSize: 540 })
  ragResults.value = result.results
}
</script>
```

### useRAGSettings (`src/composables/useRAGSettings.ts`)

Manages RAG search settings including model selection and cache configuration.

**State:**
| Property | Type | Description |
|----------|------|-------------|
| `selectedModel` | `string` | Currently selected model ID |
| `maxCachedModels` | `number` | Maximum cached models |
| `cachedModelsCount` | `number` | Current cached model count |
| `cachedModelsList` | `string[]` | List of cached model IDs |
| `models` | `RAGModel[]` | Available models |
| `currentModelInfo` | `object \| null` | Current model information |
| `isLoading` | `boolean` | Loading state |
| `error` | `string \| null` | Error message |

**Methods:**
| Method | Parameters | Description |
|--------|------------|-------------|
| `loadSettings` | None | Load all RAG settings from server |
| `switchModel` | `modelId: string` | Switch to a different model |
| `updateMaxCached` | `max: number` | Update maximum cached models |
| `evictCache` | None | Evict unused models from cache |
| `rebuildIndex` | None | Rebuild the TF-IDF index |
| `downloadModel` | `modelId: string, hfUrl?: string` | Download a model from Hugging Face |

---

## Settings Page Integration

The RAG features are accessible through the Settings page (`src/pages/settings.vue`):

**RAG Settings Tab:**
- Model selector dropdown
- Cache configuration (max cached models)
- Current model indicator
- Cache eviction button
- Index rebuild button
- Model download button

---

## Browse Page Integration

The RAG search is integrated into the Browse page (`src/pages/browse.vue`):

```vue
<script setup lang="ts">
import { useRagSearch, type SearchResult } from '~/composables/useRagSearch'
import { useLinkFiles } from '~/composables/useLinkFiles'
import { useImagePreview } from '~/composables/useImagePreview'

// RAG search state
const { search: ragSearch, clearResults: clearRagResults } = useRagSearch()
const ragResults = ref<SearchResult[]>([])
</script>
```

**Note:** The Browse page is currently a skeleton page with tab structure but no content implementation. See [`UNUSED_FILES_REVIEW.md`](UNUSED_FILES_REVIEW.md) for details.

---

## Dependencies

The Python RAG service requires the following dependencies (see [`src/py-code/rag_search/requirements.txt`](src/py-code/rag_search/requirements.txt)):

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sentence-transformers` - Embedding model library
- `torch` - Deep learning framework
- `sqlalchemy` - SQL toolkit
- `pg8000` - PostgreSQL driver
- `scikit-learn` - TF-IDF vectorization
- `scipy` - Sparse matrix operations
- `numpy` - Numerical computing

---

## Troubleshooting

### Service Not Starting

1. Verify `MODELS_DIR` exists and contains model files
2. Check database connectivity
3. Ensure port 8079 is available

### Model Loading Fails

1. Verify model directory contains `config.json` or `model.safetensors`
2. Check disk space (models require ~1-2GB each)
3. Review logs for specific error messages

### Search Returns No Results

1. Verify TF-IDF index exists in `INDEX_DIR`
2. Rebuild the index via Settings page or API
3. Check that files have tags in the database
