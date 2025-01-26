"""Deduplicates documents from the scraped dataset based on CELEX numbers."""

import json
from pathlib import Path
from typing import Dict, Set, List, Tuple
from datetime import datetime
import shutil
from loguru import logger
import os


class DocumentDeduplicator:
    """Handles deduplication of scraped documents based on CELEX numbers."""

    def __init__(self, data_dir: str):
        """Initialize the deduplicator.
        
        Args:
            data_dir: Base directory containing the scraped documents
        """
        self.data_dir = Path(data_dir)
        self.document_map: Dict[str, List[Path]] = {}  # CELEX number -> list of file paths
        
    def scan_documents(self):
        """Scan all documents and build a map of CELEX numbers to file paths."""
        logger.info(f"Scanning documents in {self.data_dir}")
        
        for json_file in self.data_dir.rglob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'metadata' in data and 'celex_number' in data['metadata']:
                        celex = data['metadata']['celex_number']
                        if celex not in self.document_map:
                            self.document_map[celex] = []
                        self.document_map[celex].append(json_file)
            except Exception as e:
                logger.error(f"Error processing {json_file}: {str(e)}")
    
    def find_duplicates(self) -> Dict[str, List[Path]]:
        """Find documents with duplicate CELEX numbers.
        
        Returns:
            Dict mapping CELEX numbers to lists of file paths for duplicates
        """
        return {celex: paths for celex, paths in self.document_map.items() 
                if len(paths) > 1}
    
    def _parse_date_from_path(self, path: Path) -> Tuple[datetime, str]:
        """Parse date from file path, handling various date formats.
        
        Args:
            path: Path object to parse date from
            
        Returns:
            Tuple of (datetime object, original date string)
        """
        try:
            # Get the date directory (which is the immediate parent of the file)
            date_dir = path.parent.name
            
            # The date directory should be in YYYYMMDD format
            if len(date_dir) == 8:  # YYYYMMDD format
                return datetime.strptime(date_dir, '%Y%m%d'), date_dir
            
            raise ValueError(f"Could not parse date from directory: {date_dir}")
        except Exception as e:
            logger.error(f"Error parsing date from path {path}: {str(e)}")
            raise
    
    def keep_earliest_date(self, duplicates: Dict[str, List[Path]], backup_dir: str = None):
        """Keep only the document from the earliest date directory for each CELEX number.
        
        Args:
            duplicates: Dict mapping CELEX numbers to lists of duplicate file paths
            backup_dir: Optional directory to backup removed duplicates
        """
        if backup_dir:
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
        
        for celex, paths in duplicates.items():
            try:
                # Sort paths by date with error handling
                dated_paths = []
                for p in paths:
                    try:
                        date, date_str = self._parse_date_from_path(p)
                        dated_paths.append((date, p, date_str))
                    except Exception as e:
                        logger.error(f"Skipping path due to date parsing error - CELEX: {celex}, Path: {p}, Error: {str(e)}")
                        continue
                
                if not dated_paths:
                    logger.error(f"No valid dates found for CELEX {celex}, skipping")
                    continue
                
                # Sort by date
                dated_paths.sort(key=lambda x: x[0])
                
                # Keep the first (earliest) file
                earliest_file = dated_paths[0][1]
                logger.info(f"Keeping {earliest_file} (date: {dated_paths[0][2]}) for CELEX {celex}")
                
                # Handle duplicates
                for _, duplicate, date_str in dated_paths[1:]:
                    if backup_dir:
                        # Create relative path structure in backup dir
                        rel_path = duplicate.relative_to(self.data_dir)
                        backup_file = backup_path / rel_path
                        backup_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(duplicate), str(backup_file))
                        logger.info(f"Moved duplicate {duplicate} (date: {date_str}) to {backup_file}")
                    else:
                        duplicate.unlink()
                        logger.info(f"Removed duplicate {duplicate} (date: {date_str})")
            except Exception as e:
                logger.error(f"Error processing duplicates for CELEX {celex}: {str(e)}")
                continue
    
    def cleanup_empty_directories(self):
        """Remove empty directories in the data directory structure.
        
        Walks the directory tree bottom-up and removes any empty directories.
        Will remove nested empty directories as well (e.g., empty day dir, then its empty month dir).
        """
        logger.info("Cleaning up empty directories...")
        empty_dirs = 0
        
        # Walk bottom-up so we can remove empty parent directories
        for dirpath, dirnames, filenames in os.walk(self.data_dir, topdown=False):
            if not dirnames and not filenames:  # Directory is empty
                try:
                    dir_to_remove = Path(dirpath)
                    # Don't remove the root data directory
                    if dir_to_remove != self.data_dir:
                        dir_to_remove.rmdir()
                        empty_dirs += 1
                        logger.info(f"Removed empty directory: {dir_to_remove}")
                except Exception as e:
                    logger.error(f"Error removing directory {dirpath}: {str(e)}")
        
        logger.info(f"Removed {empty_dirs} empty directories")
    
    def cleanup(self, backup_dir: str = None):
        """Run the complete deduplication process.
        
        Args:
            backup_dir: Optional directory to backup removed duplicates
        """
        self.scan_documents()
        duplicates = self.find_duplicates()
        
        if not duplicates:
            logger.info("No duplicates found")
        else:
            logger.info(f"Found {len(duplicates)} documents with duplicates")
            self.keep_earliest_date(duplicates, backup_dir)
            logger.info("Deduplication complete")
        
        # Clean up empty directories after deduplication
        self.cleanup_empty_directories()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Deduplicate EUR-Lex documents based on CELEX numbers")
    parser.add_argument("--data-dir", required=True, help="Base directory containing scraped documents")
    parser.add_argument("--backup-dir", help="Optional directory to backup removed duplicates")
    
    args = parser.parse_args()
    
    deduplicator = DocumentDeduplicator(args.data_dir)
    deduplicator.cleanup(args.backup_dir)
