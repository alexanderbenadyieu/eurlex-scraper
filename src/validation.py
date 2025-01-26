"""Validation module for EUR-Lex scraper."""
from datetime import datetime
from typing import Any, Dict, List, Optional
import re

from jsonschema import validate
from loguru import logger

from exceptions import ValidationError

# JSON Schema for document metadata
METADATA_SCHEMA = {
    "type": "object",
    "required": ["title", "celex_number"],
    "properties": {
        "celex_number": {"type": "string"},
        "title": {"type": "string", "minLength": 1},
        "identifier": {"type": "string"},
        "eli_uri": {"type": "string", "format": "uri"},
        "html_url": {"type": "string", "format": "uri"},
        "pdf_url": {"type": "string", "format": "uri"},
        "dates": {
            "type": "object",
            "properties": {
                "Date of document": {"type": "string"},
                "Date of effect": {"type": "string"},
                "Date of end of validity": {"type": "string"}
            }
        },
        "authors": {"type": "array", "items": {"type": "string"}},
        "responsible_body": {"type": "string"},
        "form": {"type": "string"},
        "eurovoc_descriptors": {"type": "array", "items": {"type": "string"}},
        "subject_matters": {"type": "array", "items": {"type": "string"}},
        "directory_codes": {"type": "array", "items": {"type": "string"}},
        "directory_descriptions": {"type": "array", "items": {"type": "string"}}
    }
}


def validate_metadata(metadata: Dict[str, Any]) -> None:
    """
    Validate document metadata against the schema.
    
    Args:
        metadata: Dictionary containing document metadata
        
    Raises:
        ValidationError: If metadata fails validation
    """
    try:
        # Validate identifier (optional)
        identifier = metadata.get('identifier', '').strip()
        
        # If identifier is not empty, validate its structure
        if identifier:
            # Check for specific identifier formats
            valid_identifier_pattern = r'^[A-Z]/\d{4}/\d+(/[A-Z]+)?$'
            
            if not re.match(valid_identifier_pattern, identifier):
                # If it doesn't match the expected structure, set to empty string
                metadata['identifier'] = ''
        
        # Log non-standard CELEX numbers for tracking
        if 'celex_number' in metadata and metadata['celex_number']:
            celex_num = metadata['celex_number']
            logger.info(f"CELEX number: {celex_num}")
        
        validate(instance=metadata, schema=METADATA_SCHEMA)
    except Exception as e:
        logger.error(f"Metadata validation failed: {str(e)}")
        raise ValidationError(f"Invalid metadata format: {str(e)}") from e


def validate_document_id(doc_id: str) -> bool:
    """
    Validate document ID format and check if it's a corrigendum.
    
    Args:
        doc_id: Document ID to validate
        
    Returns:
        bool: True if document is valid and not a corrigendum
    """
    if not doc_id:
        return False
    
    # Remove 'L_' prefix if present
    if doc_id.startswith('L_'):
        doc_id = doc_id[2:]
    
    # Check if it's a corrigendum (ends with 9...)
    if doc_id[4] == '9':
        return False
    
    # Basic format validation: should be a year (2025) followed by 5 digits
    return len(doc_id) == 9 and doc_id[:4].isdigit()


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse a date string in various formats.
    
    Args:
        date_str: Date string to parse
        
    Returns:
        datetime: Parsed datetime object or None if parsing fails
    """
    formats = [
        '%d/%m/%Y',  # 10/01/2025
        '%d.%m.%Y',  # 10.01.2025
        '%Y-%m-%d',  # 2025-01-10
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None
