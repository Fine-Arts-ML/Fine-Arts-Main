"""FastAPI application for RAG Search service with multi-model support."""

import os
import sys
import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .config import RAGConfig, ModelConfig
from .model_loader import ModelLoader
from .tfidf_index import TFIDFIndex
from .database import Database
from .search import RAGSearch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ─── Pydantic Models ────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    top_k: int = Field(default=24, ge=1, le=200, description="Number of results per page")
    preview_size: int = Field(default=540, ge=64, le=2048, description="Preview dimension")
    min_similarity: float = Field(default=0.25, ge=0.0, le=1.0, description="Minimum similarity threshold")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")


class SearchResponse(BaseModel):
    results: List[Dict]
    query_time_ms: float
    has_more: bool = False
    total_matching: int = 0
    min_similarity: float = 0.25
    has_more: bool = False
    total_matching: int = 0
    min_similarity: float = 0.25


class ModelInfo(BaseModel):
    id: str
    name: str
    description: str
    params: str = ""
    disk_size: str = ""
    ram_usage: str = ""
    load_time: str = ""
    downloaded: bool = False
    in_cache: bool = False


class CacheConfigRequest(BaseModel):
    max_cached: int = Field(..., ge=1, le=5, description="Max cached models")


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    index_size: int
    uptime_seconds: float
    current_model: Optional[str] = None


class ModelSwitchRequest(BaseModel):
    model_id: str


class DownloadModelRequest(BaseModel):
    model_id: str
    hf_url: str = ""


class ReindexRequest(BaseModel):
    pass


class TaskResponse(BaseModel):
    status: str
    message: str
    task_id: Optional[str] = None


# ─── Global State ────────────────────────────────────────────────────────────

config = RAGConfig()
model_loader: Optional[ModelLoader] = None
tfidf_index: Optional[TFIDFIndex] = None
database: Optional[Database] = None
rag_search: Optional[RAGSearch] = None
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources."""
    global model_loader, tfidf_index, database, rag_search
    
    logger.info("Initializing RAG Search service...")
    
    # Initialize components
    model_loader = ModelLoader(config)
    database = Database(config)
    tfidf_index = TFIDFIndex(config)
    
    # Try to load existing TF-IDF index
    loaded = tfidf_index.load_index()
    if not loaded:
        logger.info("Building new TF-IDF index from database...")
        file_documents = database.build_file_documents()
        tfidf_index.build_index(file_documents)
    
    # Initialize search
    rag_search = RAGSearch(config, model_loader, tfidf_index, database)
    
    # Skip initial model loading - load lazily on first request instead
    # This allows the service to start quickly while the model loads in the background
    default_model = config.default_model
    available = model_loader.get_available_models()
    if default_model in available:
        logger.info(f"Default model '{default_model}' will be loaded lazily on first search request")
    else:
        logger.warning(f"Default model '{default_model}' not available")
    
    logger.info("RAG Search service initialized (model loading deferred to first request)")
    yield
    
    # Cleanup
    logger.info("Shutting down RAG Search service...")


# ─── FastAPI App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="RAG Search Service",
    description="Semantic search using TF-IDF weighted embeddings with multi-model support",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/api/v1/rag/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        model_loaded=model_loader is not None and model_loader.get_current_model() is not None,
        index_size=tfidf_index.get_index_size() if tfidf_index else 0,
        uptime_seconds=time.time() - start_time,
        current_model=model_loader.get_current_model() if model_loader else None
    )


@app.post("/api/v1/rag/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Perform semantic search."""
    if not rag_search:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query is required")
    
    result = rag_search.search(
        query=request.query,
        top_k=request.top_k,
        preview_size=request.preview_size,
        min_similarity=request.min_similarity,
        offset=request.offset
    )
    
    # Add pagination info to response
    response_data = {
        "results": result["results"],
        "query_time_ms": result["query_time_ms"],
        "has_more": len(result["results"]) >= request.top_k,
        "total_matching": result.get("total_matching", None),
        "min_similarity": request.min_similarity
    }
    
    return response_data


@app.get("/api/v1/rag/models", response_model=List[ModelInfo])
async def list_models():
    """List available models."""
    if not model_loader:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    models = model_loader.get_available_models()
    cached = model_loader.get_cached_models()
    
    result = []
    for model_id, model_config in models.items():
        result.append(ModelInfo(
            id=model_id,
            name=model_config.name,
            description=model_config.description,
            params=model_config.params,
            disk_size=model_config.disk_size,
            ram_usage=model_config.ram_usage,
            load_time=model_config.load_time,
            downloaded=True,  # Discovered on disk
            in_cache=model_id in cached
        ))
    
    return result


@app.get("/api/v1/rag/models/current")
async def get_current_model():
    """Get current active model."""
    if not model_loader:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    current = model_loader.get_current_model()
    if not current:
        return {"current_model": None}
    
    models = model_loader.get_available_models()
    config_obj = models.get(current)
    
    return {
        "current_model": current,
        "model_info": {
            "id": current,
            "name": config_obj.name if config_obj else current,
            "description": config_obj.description if config_obj else ""
        } if config_obj else None
    }


@app.post("/api/v1/rag/models/switch")
async def switch_model(request: ModelSwitchRequest):
    """Switch to a different model."""
    if not model_loader:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    models = model_loader.get_available_models()
    if request.model_id not in models:
        raise HTTPException(
            status_code=400, 
            detail=f"Model '{request.model_id}' not available"
        )
    
    try:
        model_loader.switch_model(request.model_id)
        return {"status": "switched", "model": request.model_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/rag/cache/config")
async def get_cache_config():
    """Get cache configuration."""
    if not model_loader:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    cache_info = model_loader.get_cache_info()
    return {
        "max_cached": config.max_cached_models,
        "current_count": cache_info["cache_size"],
        "cached_models": cache_info["cached_models"]
    }


@app.post("/api/v1/rag/cache/config")
async def update_cache_config(request: CacheConfigRequest):
    """Update cache configuration."""
    global config
    config.max_cached_models = request.max_cached
    
    # Evict if needed
    if model_loader:
        model_loader.evict_unused_models()
    
    return {"status": "updated", "max_cached": request.max_cached}


@app.post("/api/v1/rag/cache/evict")
async def evict_cache():
    """Evict unused models from cache."""
    if not model_loader:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    model_loader.evict_unused_models()
    return {"status": "evicted"}


@app.post("/api/v1/rag/models/download")
async def download_model(request: DownloadModelRequest):
    """Download a model from HuggingFace."""
    import subprocess
    import shutil
    
    model_id = request.model_id
    hf_url = request.hf_url or f"Qwen/{model_id.replace('-', '_').title()}"
    
    # Determine the model directory name
    model_dir = os.path.join(config.models_dir, model_id)
    
    # Check if model already exists
    if os.path.isdir(model_dir):
        # Check if it has model files
        has_files = any(os.path.isfile(os.path.join(model_dir, f)) for f in os.listdir(model_dir))
        if has_files:
            raise HTTPException(status_code=400, detail=f"Model '{model_id}' already exists")
    
    os.makedirs(model_dir, exist_ok=True)
    
    try:
        logger.info(f"Downloading model '{model_id}' from {hf_url} to {model_dir}...")
        
        # Use huggingface-cli to download the model
        result = subprocess.run(
            [
                sys.executable, "-m", "huggingface_hub", "download",
                hf_url,
                "--local-dir", model_dir,
                "--local-dir-use-symlinks", "False"
            ],
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode != 0:
            logger.error(f"Download failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Download failed: {result.stderr}"
            )
        
        logger.info(f"Model '{model_id}' downloaded successfully")
        
        # Refresh available models
        models = model_loader.get_available_models()
        
        return {
            "status": "success",
            "message": f"Model '{model_id}' downloaded successfully",
            "model": {
                "id": model_id,
                "name": models.get(model_id, ModelConfig(id=model_id, name=model_id, description="", model_path=model_id)).name,
                "downloaded": True
            }
        }
        
    except subprocess.TimeoutExpired:
        logger.error(f"Download timed out for model '{model_id}'")
        raise HTTPException(status_code=500, detail="Download timed out")
    except Exception as e:
        logger.error(f"Download error for model '{model_id}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/rag/index/rebuild")
async def rebuild_index():
    """Rebuild the TF-IDF index from scratch."""
    if not tfidf_index or not database:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        logger.info("Rebuilding TF-IDF index from scratch...")
        
        # Clear existing index
        tfidf_index.vectorizer = None
        tfidf_index.matrix = None
        tfidf_index.file_ids = []
        
        # Build new index
        file_documents = database.build_file_documents()
        tfidf_index.build_index(file_documents)
        
        logger.info(f"TF-IDF index rebuilt successfully with {tfidf_index.get_index_size()} documents")
        
        return {
            "status": "success",
            "message": "TF-IDF index rebuilt successfully",
            "index_size": tfidf_index.get_index_size()
        }
        
    except Exception as e:
        logger.error(f"Index rebuild failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "rag_search.main:app",
        host=config.host,
        port=config.port,
        log_level="info"
    )
