"""Search logic for RAG search service."""

import os
import time
import json
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

from .config import RAGConfig
from .model_loader import ModelLoader
from .tfidf_index import TFIDFIndex
from .database import Database

logger = logging.getLogger(__name__)


class RAGSearch:
    """Semantic search using TF-IDF weighted embeddings."""
    
    def __init__(self, config: RAGConfig, model_loader: ModelLoader, 
                 tfidf_index: TFIDFIndex, database: Database):
        self.config = config
        self.model_loader = model_loader
        self.tfidf_index = tfidf_index
        self.database = database
        
        # Pre-computed document embeddings cache
        self._doc_embeddings: Optional[np.ndarray] = None
        self._embedding_cache_path = os.path.join(
            config.index_dir, 
            "doc_embeddings.npy"
        )
        self._embedding_meta_path = os.path.join(
            config.index_dir, 
            "doc_embeddings_meta.json"
        )
    
    def search(self, query: str, top_k: int = 24, 
               preview_size: int = 540) -> Dict:
        """
        Perform semantic search.
        
        Args:
            query: Natural language search query.
            top_k: Number of results to return.
            preview_size: Preview image size.
            
        Returns:
            Dict with 'results' list and 'query_time_ms'.
        """
        start_time = time.time()
        
        # Get current model
        model_id = self.model_loader.get_current_model()
        if not model_id:
            model_id = self.config.default_model
        model = self.model_loader.get_model(model_id)
        
        # Encode query
        query_embedding = self._encode_query(model, query)
        
        # Get pre-computed document embeddings
        file_embeddings = self._get_cached_embeddings(model)
        
        if file_embeddings is None or file_embeddings.shape[0] == 0:
            elapsed = (time.time() - start_time) * 1000
            return {"results": [], "query_time_ms": round(elapsed, 2)}
        
        file_ids = self.tfidf_index.file_ids
        
        # Compute cosine similarity
        similarities = self._compute_similarity(query_embedding, file_embeddings)
        
        # Get top-k results
        top_indices = np.argsort(similarities)[::-1][:top_k]
        top_scores = similarities[top_indices]
        
        # Fetch file metadata
        top_file_ids = [file_ids[i] for i in top_indices]
        file_metadata = self.database.get_file_metadata(top_file_ids)
        
        # Build metadata lookup
        metadata_map = {str(fm["fileid"]): fm for fm in file_metadata}
        
        # Build results
        results = []
        for idx, score in zip(top_indices, top_scores):
            file_id = file_ids[idx]
            metadata = metadata_map.get(file_id, {})
            
            result = {
                "file_id": int(file_id) if file_id.isdigit() else file_id,
                "filename": metadata.get("name", ""),
                "similarity": round(float(score), 4),
                "preview_url": self._build_preview_url(
                    metadata.get("preview_url", ""), 
                    preview_size
                ),
            }
            results.append(result)
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"Search completed: {len(results)} results in {elapsed:.2f}ms")
        
        return {
            "results": results,
            "query_time_ms": round(elapsed, 2)
        }
    
    def _encode_query(self, model, query: str) -> np.ndarray:
        """Encode query to embedding vector using prompt-based encoding."""
        with torch.no_grad():
            embedding = model.encode(
                query,
                prompt_name="query",
                convert_to_numpy=True,
                normalize_embeddings=True
            )
        return embedding.flatten()
    
    def _get_cached_embeddings(self, model) -> Optional[np.ndarray]:
        """
        Get document embeddings, computing and caching if necessary.
        
        Returns pre-computed embeddings from disk if available and valid,
        otherwise computes them, caches to disk, and returns them.
        """
        # Check if we already have embeddings in memory
        if self._doc_embeddings is not None:
            return self._doc_embeddings
        
        # Try to load from disk
        if self._try_load_embeddings_from_disk():
            return self._doc_embeddings
        
        # Compute embeddings
        logger.info("No cached embeddings found. Computing document embeddings...")
        embeddings = self._compute_all_document_embeddings(model)
        
        if embeddings is not None:
            # Save to disk for future use
            self._save_embeddings_to_disk(embeddings)
        
        return embeddings
    
    def _try_load_embeddings_from_disk(self) -> bool:
        """Try to load pre-computed embeddings from disk."""
        if not os.path.exists(self._embedding_cache_path):
            logger.info("No cached document embeddings found on disk")
            return False
        
        try:
            logger.info("Loading cached document embeddings from disk...")
            self._doc_embeddings = np.load(self._embedding_cache_path)
            
            # Validate metadata
            if os.path.exists(self._embedding_meta_path):
                with open(self._embedding_meta_path, 'r') as f:
                    meta = json.load(f)
                
                # Check if index matches
                if meta.get("doc_count") != self.tfidf_index.get_index_size():
                    logger.warning(
                        f"Embedding cache mismatch: cached={meta.get('doc_count')}, "
                        f"current={self.tfidf_index.get_index_size()}. "
                        f"Will recompute."
                    )
                    self._doc_embeddings = None
                    return False
            
            logger.info(
                f"Loaded cached embeddings: shape={self._doc_embeddings.shape}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to load cached embeddings: {e}")
            self._doc_embeddings = None
            return False
    
    def _compute_all_document_embeddings(self, model) -> Optional[np.ndarray]:
        """
        Compute embeddings for all TF-IDF weighted documents.
        
        This is expensive and should only be done once, then cached.
        """
        if self.tfidf_index.matrix is None or self.tfidf_index.file_ids is None:
            logger.error("TF-IDF index not available for embedding computation")
            return None
        
        file_ids = self.tfidf_index.file_ids
        tfidf_matrix = self.tfidf_index.matrix
        vectorizer = self.tfidf_index.vectorizer
        
        if vectorizer is None:
            logger.error("TF-IDF vectorizer not available")
            return None
        
        # Reconstruct weighted documents from TF-IDF matrix
        logger.info("Converting TF-IDF matrix to weighted documents...")
        weighted_docs = self._tfidf_to_text(
            tfidf_matrix, 
            vectorizer
        )
        logger.info(f"Created {len(weighted_docs)} weighted documents")
        
        # Encode all documents at once for efficiency
        logger.info(
            f"Encoding {len(weighted_docs)} documents (this may take a few minutes)..."
        )
        encode_start = time.time()
        
        with torch.no_grad():
            embeddings = model.encode(
                weighted_docs,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=64,
                show_progress_bar=True
            )
        
        encode_time = time.time() - encode_start
        logger.info(f"Document encoding completed in {encode_time:.1f}s")
        
        self._doc_embeddings = embeddings
        return embeddings
    
    def _save_embeddings_to_disk(self, embeddings: np.ndarray):
        """Save document embeddings to disk for persistence."""
        try:
            # Ensure index directory exists
            os.makedirs(os.path.dirname(self._embedding_cache_path), exist_ok=True)
            
            # Save embeddings
            np.save(self._embedding_cache_path, embeddings)
            logger.info(f"Saved document embeddings to {self._embedding_cache_path}")
            
            # Save metadata
            meta = {
                "doc_count": embeddings.shape[0],
                "embedding_dim": embeddings.shape[1],
                "file_count": len(self.tfidf_index.file_ids),
                "tfidf_index_size": self.tfidf_index.get_index_size(),
                "created_at": time.time()
            }
            
            with open(self._embedding_meta_path, 'w') as f:
                json.dump(meta, f, indent=2)
            
            logger.info(f"Saved embedding metadata to {self._embedding_meta_path}")
            
        except Exception as e:
            logger.error(f"Failed to save embeddings to disk: {e}")
    
    def invalidate_cache(self):
        """Invalidate the in-memory embedding cache."""
        self._doc_embeddings = None
        logger.info("Document embedding cache invalidated")
    
    def _tfidf_to_text(self, tfidf_matrix, vectorizer, repeat_factor: int = 3) -> List[str]:
        """
        Convert TF-IDF sparse matrix back to weighted text documents.
        
        Tags with higher TF-IDF scores are repeated more times,
        giving them more weight in the embedding.
        """
        vocabulary = vectorizer.vocabulary_
        inv_vocab = {v: k for k, v in vocabulary.items()}
        
        weighted_docs = []
        for i in range(tfidf_matrix.shape[0]):
            row = tfidf_matrix.getrow(i)
            indices = row.nonzero()[1]
            scores = row.data
            
            # Sort by TF-IDF score descending
            sorted_order = np.argsort(scores)[::-1]
            indices = indices[sorted_order]
            scores = scores[sorted_order]
            
            # Repeat tags based on score
            weighted_tags = []
            for idx, score in zip(indices, scores):
                tag = inv_vocab[idx]
                repeats = max(1, int(score * repeat_factor))
                weighted_tags.extend([tag] * repeats)
            
            weighted_docs.append(" ".join(weighted_tags))
        
        return weighted_docs
    
    def _compute_similarity(self, query_embedding: np.ndarray, 
                           file_embeddings: np.ndarray) -> np.ndarray:
        """Compute cosine similarity between query and all file embeddings."""
        # Both are already normalized, so dot product = cosine similarity
        similarities = file_embeddings @ query_embedding
        return similarities
    
    def _build_preview_url(self, preview_url: str, preview_size: int) -> str:
        """Build preview URL with {prevsize} placeholder for client-side transformation."""
        if not preview_url:
            return ""
        
        # Keep the {prevsize} placeholder for client-side transformation
        # The TypeScript transformPreviewUrl function will replace it with actual dimensions
        if "{prevsize}" not in preview_url:
            separator = '&' if '?' in preview_url else '?'
            preview_url = f"{preview_url}{separator}{{prevsize}}"
        
        return preview_url
