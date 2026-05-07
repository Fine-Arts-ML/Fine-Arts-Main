"""Database queries for RAG Search service."""

from typing import Dict, List, Optional
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from .config import RAGConfig

logger = logging.getLogger(__name__)


class Database:
    """Database connection and query handler."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.engine = create_engine(config.get_connection_string())
        self.session_factory = sessionmaker(bind=self.engine)
    
    def get_session(self):
        """Get a new database session."""
        return self.session_factory()
    
    def get_all_tags(self) -> List[Dict]:
        """
        Get all system tags.
        
        Returns:
            List of dicts with 'id' and 'name' keys.
        """
        session = self.get_session()
        try:
            result = session.execute(
                text("SELECT id, name FROM oc_systemtag")
            )
            tags = [{"id": row[0], "name": row[1]} for row in result.fetchall()]
            logger.info(f"Loaded {len(tags)} tags from database")
            return tags
        finally:
            session.close()
    
    def get_tag_mappings(self) -> List[Dict]:
        """
        Get all tag-to-file mappings.
        
        Returns:
            List of dicts with 'systemtagid', 'objectid', and 'name' keys.
        """
        session = self.get_session()
        try:
            result = session.execute(
                text("""
                    SELECT om.systemtagid, om.objectid, st.name
                    FROM oc_systemtag_object_mapping om
                    INNER JOIN oc_systemtag st ON om.systemtagid = st.id
                    WHERE om.objecttype = 'files'
                """)
            )
            mappings = [
                {"systemtagid": row[0], "objectid": row[1], "name": row[2]}
                for row in result.fetchall()
            ]
            logger.info(f"Loaded {len(mappings)} tag mappings from database")
            return mappings
        finally:
            session.close()
    
    def build_file_documents(self) -> Dict[str, str]:
        """
        Build file documents by aggregating all tags for each file.
        
        Returns:
            Dict mapping file_id (str) to space-separated tag string.
        """
        mappings = self.get_tag_mappings()
        
        # Group tags by file_id
        file_tags: Dict[str, List[str]] = {}
        for mapping in mappings:
            file_id = str(mapping["objectid"])
            if file_id not in file_tags:
                file_tags[file_id] = []
            file_tags[file_id].append(mapping["name"])
        
        # Sort tags alphabetically and deduplicate
        file_documents = {}
        for file_id, tags in file_tags.items():
            sorted_tags = sorted(set(tags))
            file_documents[file_id] = " ".join(sorted_tags)
        
        logger.info(f"Built {len(file_documents)} file documents")
        return file_documents
    
    def get_file_metadata(self, file_ids: List[str]) -> List[Dict]:
        """
        Get file metadata (name, preview_url) for given file IDs.
        
        Args:
            file_ids: List of file IDs (as strings or integers).
            
        Returns:
            List of dicts with 'fileid', 'name', and 'preview_url'.
        """
        session = self.get_session()
        try:
            # Convert to integer IDs
            int_ids = [int(fid) for fid in file_ids if fid.isdigit()]
            if not int_ids:
                return []
            
            # Use named parameters for SQLAlchemy compatibility
            placeholders = ",".join([f":fid{i}" for i in range(len(int_ids))])
            params = {f"fid{i}": str(val) for i, val in enumerate(int_ids)}
            result = session.execute(
                text(f"""
                    SELECT fileid, name, preview_url
                    FROM bre_advance_index
                    WHERE fileid IN ({placeholders})
                """),
                params
            )
            files = [
                {
                    "fileid": row[0],
                    "name": row[1],
                    "preview_url": row[2]
                }
                for row in result.fetchall()
            ]
            logger.info(f"Retrieved metadata for {len(files)} files")
            return files
        finally:
            session.close()
    
    def get_file_tags(self, file_id: str) -> List[str]:
        """
        Get all tags for a specific file.
        
        Args:
            file_id: The file ID.
            
        Returns:
            List of tag names.
        """
        session = self.get_session()
        try:
            result = session.execute(
                text("""
                    SELECT st.name
                    FROM oc_systemtag_object_mapping om
                    INNER JOIN oc_systemtag st ON om.systemtagid = st.id
                    WHERE om.objecttype = 'files' AND om.objectid = :file_id
                    ORDER BY st.name
                """),
                {"file_id": int(file_id)}
            )
            tags = [row[0] for row in result.fetchall()]
            return tags
        finally:
            session.close()
