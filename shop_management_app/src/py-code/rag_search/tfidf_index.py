"""TF-IDF vectorization and index building."""

import os
import json
import logging
from typing import Dict, List, Tuple, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import save_npz, load_npz

from .config import RAGConfig

logger = logging.getLogger(__name__)


class TFIDFIndex:
    """Manages TF-IDF vectorization and index persistence."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.matrix = None
        self.file_ids: List[str] = []
        self._index_path = os.path.join(config.index_dir, "tfidf_matrix.npz")
        self._meta_path = os.path.join(config.index_dir, "tfidf_meta.json")
    
    def build_index(self, file_documents: Dict[str, str]) -> Tuple[TfidfVectorizer, np.ndarray]:
        """
        Build TF-IDF index from file documents.
        
        Args:
            file_documents: Dict mapping file_id to space-separated tag string.
            
        Returns:
            Tuple of (vectorizer, sparse matrix).
        """
        logger.info(f"Building TF-IDF index for {len(file_documents)} documents...")
        
        # Sort file IDs for consistent ordering
        self.file_ids = sorted(file_documents.keys())
        doc_texts = [file_documents[fid] for fid in self.file_ids]
        
        # Fit TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b\w+\b')
        self.matrix = self.vectorizer.fit_transform(doc_texts)
        
        logger.info(f"TF-IDF matrix shape: {self.matrix.shape}")
        logger.info(f"Vocabulary size: {len(self.vectorizer.vocabulary_)}")
        
        # Save index
        self._save_index()
        
        return self.vectorizer, self.matrix
    
    def load_index(self) -> bool:
        """
        Load pre-computed TF-IDF index from disk.
        
        Returns:
            True if index was loaded successfully, False otherwise.
        """
        if not os.path.exists(self._index_path) or not os.path.exists(self._meta_path):
            logger.info("No existing TF-IDF index found on disk")
            return False
        
        try:
            logger.info("Loading TF-IDF index from disk...")
            self.matrix = load_npz(self._index_path)
            
            with open(self._meta_path, 'r') as f:
                meta = json.load(f)
            
            self.vectorizer = TfidfVectorizer()
            self.vectorizer.vocabulary_ = {k: int(v) for k, v in meta["vocabulary"].items()}
            self.file_ids = meta["file_ids"]
            
            logger.info(f"Loaded TF-IDF index: shape={self.matrix.shape}, files={len(self.file_ids)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load TF-IDF index: {e}")
            return False
    
    def save_index(self):
        """Save TF-IDF index to disk."""
        if self.vectorizer is None or self.matrix is None:
            logger.warning("Cannot save index: vectorizer or matrix is None")
            return
        
        # Ensure index directory exists
        os.makedirs(os.path.dirname(self._index_path), exist_ok=True)
        
        try:
            save_npz(self._index_path, self.matrix)
            
            meta = {
                "vocabulary": {k: v for k, v in self.vectorizer.vocabulary_.items()},
                "file_ids": self.file_ids,
                "matrix_shape": list(self.matrix.shape),
                "vocabulary_size": len(self.vectorizer.vocabulary_)
            }
            
            with open(self._meta_path, 'w') as f:
                json.dump(meta, f)
            
            logger.info(f"Saved TF-IDF index to {self._index_path}")
            
        except Exception as e:
            logger.error(f"Failed to save TF-IDF index: {e}")
    
    def _save_index(self):
        """Persist the current index to disk."""
        self.save_index()
    
    def get_idf_weights(self) -> Dict[str, float]:
        """
        Get IDF weights for all terms.
        
        Returns:
            Dict mapping term to IDF weight.
        """
        if self.vectorizer is None:
            return {}
        
        idf = self.vectorizer.idf_
        vocab = self.vectorizer.vocabulary_
        
        return {
            term: float(weight) 
            for term, idx in vocab.items() 
            if idx < len(idf)
        }
    
    def get_index_size(self) -> int:
        """Get the number of documents in the index."""
        if self.matrix is None:
            return 0
        return self.matrix.shape[0]
