"""Embedding model loading and caching management."""

import os
import logging
from typing import Optional, Dict, List
from pathlib import Path

import torch
from sentence_transformers import SentenceTransformer

from .config import RAGConfig, ModelConfig

logger = logging.getLogger(__name__)


class ModelLoader:
    """Manages loading, caching, and unloading of embedding models."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self._cache: Dict[str, SentenceTransformer] = {}
        self._last_used: Dict[str, float] = {}
        self._current_model: Optional[str] = None
        self._model_initialized: Dict[str, bool] = {}
    
    def get_available_models(self) -> Dict[str, ModelConfig]:
        """Get list of available models (only those actually discovered on disk)."""
        models = {}
        
        # Discover models on disk only
        if os.path.isdir(self.config.models_dir):
            discovered = set()
            for item in os.listdir(self.config.models_dir):
                model_path = os.path.join(self.config.models_dir, item)
                if os.path.isdir(model_path):
                    # Check if it contains model files
                    has_config = os.path.exists(os.path.join(model_path, "config.json")) or \
                                 os.path.exists(os.path.join(model_path, "model.safetensors")) or \
                                 any(f.endswith(".gguf") for f in os.listdir(model_path) if os.path.isfile(os.path.join(model_path, f)))
                    if has_config:
                        discovered.add(item)
                        models[item] = ModelConfig(
                            id=item,
                            name=item.replace("-", " ").title(),
                            description="Embedding model",
                            model_path=item,
                            disk_size=self._get_dir_size(model_path),
                            ram_usage="~varies",
                            load_time="~varies"
                        )
            
            logger.info(f"Discovered models: {discovered}")
        else:
            logger.warning(f"Models directory does not exist: {self.config.models_dir}")
        
        return models
    
    def load_model(self, model_id: str) -> SentenceTransformer:
        """
        Load a model into cache.
        
        Args:
            model_id: The model identifier.
            
        Returns:
            The loaded SentenceTransformer model.
            
        Raises:
            ValueError: If model is not found.
            RuntimeError: If model fails to load.
        """
        # Check if already loaded
        if model_id in self._cache:
            self._last_used[model_id] = torch.cuda.current_timestamp() if torch.cuda.is_available() else 0
            logger.info(f"Model '{model_id}' already loaded from cache")
            return self._cache[model_id]
        
        # Get model path
        model_config = self.config.available_models.get(model_id)
        if not model_config:
            # Try to find on disk anyway
            model_path = os.path.join(self.config.models_dir, model_id)
            if not os.path.isdir(model_path):
                raise ValueError(f"Model '{model_id}' not found in available models or models directory")
        else:
            model_path = self.config.get_model_path(model_id)
        
        logger.info(f"Loading model '{model_id}' from {model_path}...")
        
        try:
            model = SentenceTransformer(model_path)
            self._cache[model_id] = model
            self._last_used[model_id] = 0
            self._current_model = model_id
            self._model_initialized[model_id] = True
            
            # Evict unused models if cache is full
            self._evict_unused()
            
            logger.info(f"Model '{model_id}' loaded successfully")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model '{model_id}': {e}")
            raise RuntimeError(f"Failed to load model '{model_id}': {e}")
    
    def get_model(self, model_id: str) -> SentenceTransformer:
        """Get a model, loading it if necessary."""
        if model_id not in self._cache:
            return self.load_model(model_id)
        return self._cache[model_id]
    
    def switch_model(self, model_id: str) -> SentenceTransformer:
        """
        Switch to a different model.
        
        Args:
            model_id: The new model identifier.
            
        Returns:
            The newly loaded model.
        """
        model = self.load_model(model_id)
        self._current_model = model_id
        return model
    
    def get_current_model(self) -> Optional[str]:
        """Get the current active model ID."""
        return self._current_model
    
    def get_cached_models(self) -> List[str]:
        """Get list of currently cached model IDs."""
        return list(self._cache.keys())
    
    def get_cache_info(self) -> Dict:
        """Get cache statistics."""
        return {
            "cached_models": list(self._cache.keys()),
            "current_model": self._current_model,
            "cache_size": len(self._cache),
            "max_cache_size": self.config.max_cached_models
        }
    
    def _evict_unused(self):
        """Evict unused models if cache exceeds max size."""
        while len(self._cache) > self.config.max_cached_models:
            # Find model to evict (not current, least recently used)
            models_to_consider = [
                mid for mid in self._cache 
                if mid != self._current_model
            ]
            
            if not models_to_consider:
                break
            
            # For simplicity, evict first non-current model
            to_evict = models_to_consider[0]
            self._unload_model(to_evict)
            logger.info(f"Evicted model '{to_evict}' from cache")
    
    def _unload_model(self, model_id: str):
        """Unload a model from cache."""
        if model_id in self._cache:
            del self._cache[model_id]
        if model_id in self._last_used:
            del self._last_used[model_id]
        if model_id in self._model_initialized:
            del self._model_initialized[model_id]
        
        # Force garbage collection
        import gc
        gc.collect()
    
    def evict_unused_models(self):
        """Evict models that are not currently in use, keeping only the current model."""
        if self._current_model and self._current_model in self._cache:
            models_to_keep = {self._current_model}
        else:
            models_to_keep = set()
        
        models_to_evict = [mid for mid in self._cache if mid not in models_to_keep]
        
        for model_id in models_to_evict:
            self._unload_model(model_id)
        
        logger.info(f"Evicted {len(models_to_evict)} unused models")
    
    def _get_dir_size(self, path: str) -> str:
        """Get human-readable directory size."""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    total += os.path.getsize(fp)
        
        if total > 1024 ** 3:
            return f"~{total / (1024 ** 3):.1f}GB"
        elif total > 1024 ** 2:
            return f"~{total / (1024 ** 2):.1f}MB"
        else:
            return f"~{total / 1024:.1f}KB"
