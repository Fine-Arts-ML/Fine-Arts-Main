"""Configuration for the RAG Search service."""

import os
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ModelConfig:
    """Configuration for a single embedding model."""
    id: str
    name: str
    description: str
    model_path: str  # Path inside container to model files
    params: str = ""
    disk_size: str = ""
    ram_usage: str = ""
    load_time: str = ""


@dataclass
class RAGConfig:
    """Main configuration for the RAG Search service."""
    
    # Database configuration
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "shop_management")
    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "postgres")
    
    # Model configuration
    models_dir: str = os.getenv("MODELS_DIR", "/py-code/Models")
    default_model: str = os.getenv("DEFAULT_MODEL", "qwen3-0.6b")
    max_cached_models: int = int(os.getenv("MAX_CACHED_MODELS", "1"))
    
    # Available models
    available_models: Dict[str, ModelConfig] = field(default_factory=lambda: {
        "minilm-l6": ModelConfig(
            id="minilm-l6",
            name="MiniLM-L6",
            description="Fast inference, good accuracy for simple queries",
            model_path="minilm-l6",
            params="22M",
            disk_size="~100MB",
            ram_usage="~200MB",
            load_time="~2 seconds"
        ),
        "qwen3-0.6b": ModelConfig(
            id="qwen3-0.6b",
            name="Qwen3-0.6B",
            description="Best accuracy, recommended for production",
            model_path="qwen3-0.6b",
            params="600M",
            disk_size="~1.2GB",
            ram_usage="~1.5GB",
            load_time="~10 seconds"
        ),
        "qwen2b-q4": ModelConfig(
            id="qwen2b-q4",
            name="Qwen2B-Q4",
            description="Balanced accuracy and speed (4-bit quantized)",
            model_path="qwen2b-q4",
            params="2B",
            disk_size="~1.5GB",
            ram_usage="~2GB",
            load_time="~8 seconds"
        ),
    })
    
    # Search configuration
    default_top_k: int = 24
    default_preview_size: int = 540
    
    # Server configuration
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8079"))
    
    # TF-IDF index path
    index_dir: str = os.getenv("INDEX_DIR", "/data/tfidf-index")
    
    def get_connection_string(self) -> str:
        """Get SQLAlchemy connection string."""
        return f"postgresql+pg8000://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    def get_model_path(self, model_id: str) -> str:
        """Get full path to a model directory."""
        model_config = self.available_models.get(model_id, {})
        model_path = getattr(model_config, 'model_path', model_id) if hasattr(model_config, 'model_path') else model_id
        return os.path.join(self.models_dir, model_path)
