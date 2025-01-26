"""Tracks already processed documents to prevent duplicates."""

import json
from pathlib import Path
from typing import Set
from loguru import logger


class DocumentTracker:
    """Tracks CELEX numbers of processed documents to prevent duplicates."""
    
    def __init__(self, data_dir: str):
        """Initialize the document tracker.
        
        Args:
            data_dir: Base directory containing the scraped documents
        """
        self.data_dir = Path(data_dir)
        self.processed_celex: Set[str] = set()
        self._load_existing_documents()
    
    def _load_existing_documents(self):
        """Load CELEX numbers from existing documents."""
        logger.info(f"Loading existing documents from {self.data_dir}")
        
        for json_file in self.data_dir.rglob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'metadata' in data and 'celex_number' in data['metadata']:
                        self.processed_celex.add(data['metadata']['celex_number'])
            except Exception as e:
                logger.error(f"Error processing {json_file}: {str(e)}")
        
        logger.info(f"Loaded {len(self.processed_celex)} existing documents")
    
    def is_processed(self, celex_number: str) -> bool:
        """Check if a document has already been processed.
        
        Args:
            celex_number: CELEX number to check

        Returns:
            True if the document has already been processed, False otherwise
        """
        return celex_number in self.processed_celex
    
    def mark_processed(self, celex_number: str):
        """Mark a document as processed.
        
        Args:
            celex_number: CELEX number to mark as processed
        """
        self.processed_celex.add(celex_number)
    
    def get_processed_count(self) -> int:
        """Get the number of processed documents.
        
        Returns:
            Number of processed documents
        """
        return len(self.processed_celex)
