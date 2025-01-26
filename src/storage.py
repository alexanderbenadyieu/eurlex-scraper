"""Storage module for EUR-Lex scraper."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from exceptions import StorageError
from validation import validate_metadata


class StorageManager:
    """Manages storage of scraped documents and metadata."""
    
    def __init__(self, base_dir: str):
        """
        Initialize storage manager.
        
        Args:
            base_dir: Base directory for storing documents
        """
        self.base_dir = Path(base_dir)
        self._ensure_directory_exists(self.base_dir)
    
    def _ensure_directory_exists(self, directory: Path) -> None:
        """Create directory if it doesn't exist."""
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {str(e)}")
            raise StorageError(f"Failed to create directory {directory}") from e
    
    def _get_document_path(self, date: datetime, journal_id: str, doc_id: str) -> Path:
        """
        Generate the full path for a document.
        
        Args:
            date: Document date
            journal_id: Journal identifier
            doc_id: Document identifier
            
        Returns:
            Path: Full path to the document file
        """
        # Create path: year/month/journal/document.json
        year_dir = self.base_dir / str(date.year)
        month_dir = year_dir / f"{date.month:02d}"
        journal_dir = month_dir / journal_id
        
        # Ensure all directories exist
        self._ensure_directory_exists(journal_dir)
        
        return journal_dir / f"{doc_id}.json"
    
    def store_document(self, 
                      document: Dict[str, Any],
                      date: datetime,
                      journal_id: str,
                      doc_id: str) -> Path:
        """
        Store a document as JSON.
        
        Args:
            document: Document content and metadata
            date: Document date
            journal_id: Journal identifier
            doc_id: Document identifier
            
        Returns:
            Path: Path where the document was stored
            
        Raises:
            StorageError: If storing fails
        """
        try:
            # Validate metadata if present
            if 'metadata' in document and document['metadata']:
                validate_metadata(document['metadata'])
            
            # Convert document to JSON-serializable format
            json_doc = {
                'metadata': document.get('metadata'),
                'content': document['full_text']
            }
            
            # Get storage path
            file_path = self._get_document_path(date, journal_id, doc_id)
            
            # Store document
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_doc, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Stored document {doc_id} at {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to store document {doc_id}: {str(e)}")
            raise StorageError(f"Failed to store document {doc_id}") from e
    
    def document_exists(self, date: datetime, journal_id: str, doc_id: str) -> bool:
        """
        Check if a document already exists.
        
        Args:
            date: Document date
            journal_id: Journal identifier
            doc_id: Document identifier
            
        Returns:
            bool: True if document exists
        """
        file_path = self._get_document_path(date, journal_id, doc_id)
        return file_path.exists()
    
    def load_document(self, 
                     date: datetime,
                     journal_id: str,
                     doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a stored document.
        
        Args:
            date: Document date
            journal_id: Journal identifier
            doc_id: Document identifier
            
        Returns:
            Optional[Dict[str, Any]]: Document content and metadata if exists
        """
        try:
            file_path = self._get_document_path(date, journal_id, doc_id)
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to load document {doc_id}: {str(e)}")
            return None
