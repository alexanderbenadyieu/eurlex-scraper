"""Scraper for EUR-Lex documents."""
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config_manager import ConfigManager
from document_tracker import DocumentTracker
from exceptions import ParseError, ScrapingError
from metrics import MetricsCollector
from parsers import DocumentContent, DocumentParser, MetadataParser
from storage import StorageManager
from validation import validate_document_id


class EURLexScraper:
    """Scraper for EUR-Lex legislative documents."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize the scraper with configuration."""
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.get_scraping_config()
        self.base_url = self.config['base_url']
        
        # Initialize parsers
        self.doc_parser = DocumentParser(self.base_url)
        self.metadata_parser = MetadataParser()
        
        # Initialize storage
        storage_config = self.config_manager.get_storage_config()
        self.storage = StorageManager(storage_config['base_dir'])
        
        # Initialize document tracker
        self.tracker = DocumentTracker(storage_config['base_dir'])
        
        # Initialize metrics
        metrics_config = self.config_manager.get_metrics_config()
        if metrics_config['enabled']:
            self.metrics = MetricsCollector(
                metrics_dir=metrics_config.get('directory'),
                export_port=metrics_config.get('export_port')
            )
        else:
            self.metrics = None
        
        # Initialize session and user agent
        self.user_agent = UserAgent()
        self.session = self._init_session()
    
    def _init_session(self) -> requests.Session:
        """Initialize a requests session with proper headers."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.user_agent.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        return session
    
    def _rotate_user_agent(self) -> None:
        """Rotate the user agent."""
        self.session.headers['User-Agent'] = self.user_agent.random
    
    def get_journal_url(self, date: datetime) -> str:
        """Generate the URL for a specific journal date."""
        date_str = date.strftime("%d%m%Y")
        url = f"{self.base_url}/oj/daily-view/L-series/default.html?ojDate={date_str}"
        logger.debug(f"Generated journal URL: {url}")
        return url
    
    def get_document_url(self, doc_id: str, view_type: str = 'ALL') -> str:
        """Generate the URL for a specific document view."""
        if view_type == 'ALL':
            url = f"{self.base_url}/legal-content/EN/ALL/?uri=OJ:L_{doc_id}"
        else:
            url = f"{self.base_url}/legal-content/EN/TXT/?uri=OJ:L_{doc_id}"
        logger.debug(f"Generated document URL: {url} for view type: {view_type}")
        return url
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True
    )
    def fetch_page(self, url: str) -> str:
        """Fetch a page with retry logic."""
        try:
            logger.debug(f"Fetching URL: {url}")
            response = self.session.get(url, timeout=self.config['request_timeout'])
            response.raise_for_status()
            
            if self.metrics:
                self.metrics.record_request(success=True, url=url)
                self.metrics.record_debug_event('page_fetch_success', f"Status code: {response.status_code}")
            
            logger.debug(f"Successfully fetched URL: {url}")
            return response.text
            
        except requests.RequestException as e:
            if self.metrics:
                self.metrics.record_request(success=False, url=url)
                self.metrics.record_retry_attempt(url=url)
                self.metrics.record_debug_event('page_fetch_error', str(e))
            
            logger.error(f"Failed to fetch {url}: {str(e)}")
            raise ScrapingError(f"Failed to fetch {url}") from e
            
        finally:
            self._rotate_user_agent()
    
    def extract_document_links(self, html_content: str) -> List[Dict[str, str]]:
        """Extract document links from journal page."""
        soup = BeautifulSoup(html_content, 'html.parser')
        documents = []
        
        try:
            # Debug the HTML structure
            logger.debug("Analyzing journal page structure...")
            logger.debug(f"Found {len(soup.find_all('a'))} total links")
            
            # Look for links in the main content area
            main_content = soup.find('div', {'id': 'MainContent'})
            if not main_content:
                logger.debug("No main content found on page")
                if self.metrics:
                    self.metrics.record_debug_event('page_structure', "No main content found")
                return []
            
            # Find all links that could be document links
            for link in main_content.find_all('a', href=True):
                href = link.get('href', '')
                logger.debug(f"Analyzing link: {href}")
                
                # Look for links to legal content
                if not href or 'legal-content/EN/' not in href:
                    continue
                
                # Extract document ID from URL
                try:
                    # Format: /legal-content/EN/TXT/?uri=OJ:L_202401015
                    if 'uri=OJ:L_' in href:
                        doc_id = href.split('uri=OJ:L_')[-1].split('&')[0]
                    else:
                        continue
                        
                    logger.debug(f"Found document ID: {doc_id}")
                    
                    # Validate document ID
                    if not validate_document_id(doc_id):
                        if self.metrics:
                            self.metrics.record_validation_error('document_id', f"Invalid ID: {doc_id}")
                        logger.debug(f"Skipping invalid or corrigendum document: {doc_id}")
                        continue
                    
                    # Get the title from the link text or a nearby element
                    title = link.text.strip()
                    if not title and link.parent:
                        title = link.parent.text.strip()
                    
                    doc_info = {
                        'url': urljoin(self.base_url, href),
                        'title': title,
                        'document_id': doc_id
                    }
                    logger.debug(f"Found valid document: {doc_info}")
                    documents.append(doc_info)
                    
                except Exception as e:
                    logger.debug(f"Failed to parse document ID from URL {href}: {str(e)}")
                    if self.metrics:
                        self.metrics.record_validation_error('url_parsing', f"URL: {href}, Error: {str(e)}")
            
            logger.info(f"Found {len(documents)} valid documents")
            if self.metrics:
                self.metrics.record_debug_event('documents_found', f"Count: {len(documents)}")
            
            return documents
            
        except Exception as e:
            if self.metrics:
                self.metrics.record_debug_event('link_extraction_error', str(e))
            logger.error(f"Failed to parse document links: {str(e)}")
            raise ParseError("Failed to extract document links from journal page") from e
    
    def scrape_document(self, doc_id: str, date: datetime, journal_id: str) -> Optional[Path]:
        """Scrape a single document."""
        try:
            # Start timing document processing
            with self.metrics.time_document_processing(doc_id) if self.metrics else nullcontext():
                logger.debug(f"Starting to scrape document {doc_id}")
                
                # Check if document already exists using DocumentTracker
                metadata_html = self.fetch_page(self.get_document_url(doc_id, 'ALL'))
                metadata = self.metadata_parser.parse_metadata(metadata_html)
                celex = metadata['celex_number']
                
                if self.tracker.is_processed(celex):
                    logger.info(f"Document {celex} already processed, skipping")
                    return None
                
                # Fetch document content
                content_html = self.fetch_page(self.get_document_url(doc_id, 'TXT'))
                
                # Parse content
                content = self.doc_parser.parse_document(content_html, doc_id)
                
                # Create document dictionary
                document = {
                    'metadata': {
                        'celex_number': metadata['celex_number'],
                        'title': metadata['title'],
                        'identifier': metadata['identifier'],
                        'eli_uri': metadata['eli_uri'],
                        'html_url': content.html_url,
                        'pdf_url': content.pdf_url,
                        'dates': metadata['dates'],
                        'authors': metadata['authors'],
                        'responsible_body': metadata['responsible_body'],
                        'form': metadata['form'],
                        'eurovoc_descriptors': metadata['eurovoc_descriptors'],
                        'subject_matters': metadata['subject_matters'],
                        'directory_codes': metadata['directory_codes'],
                        'directory_descriptions': metadata['directory_descriptions']
                    },
                    'full_text': content.full_text
                }
                
                # Store document
                path = self.storage.store_document(
                    document=document,
                    date=date,
                    journal_id=journal_id,
                    doc_id=doc_id
                )
                
                # Mark document as processed
                self.tracker.mark_processed(celex)
                
                # Update metrics
                if self.metrics:
                    self.metrics.record_document_processed(success=True, date=date.strftime('%Y-%m-%d'))
                    self.metrics.update_storage_size(Path(self.storage.base_dir))
                    self.metrics.record_debug_event('document_processed', f"Document {doc_id} processed successfully")
                
                logger.debug(f"Successfully scraped document {doc_id}")
                return path
                
        except Exception as e:
            if self.metrics:
                self.metrics.record_document_processed(success=False, date=date.strftime('%Y-%m-%d'))
                self.metrics.record_debug_event('document_processing_error', f"Document {doc_id}: {str(e)}")
            logger.error(f"Failed to scrape document {doc_id}: {str(e)}")
            return None
    
    def scrape_journal(self, date: datetime) -> List[Path]:
        """Scrape all documents from a journal."""
        try:
            # Start timing journal processing
            date_str = date.strftime('%Y-%m-%d')
            with self.metrics.time_journal_processing(date_str) if self.metrics else nullcontext():
                logger.debug(f"Starting to scrape journal for date: {date_str}")
                
                # Generate journal URL and ID
                journal_url = self.get_journal_url(date)
                journal_id = date.strftime("%Y%m%d")
                
                # Fetch journal page
                journal_html = self.fetch_page(journal_url)
                
                # Extract document links
                documents = self.extract_document_links(journal_html)
                
                # Scrape each document
                stored_paths = []
                for doc in documents:
                    path = self.scrape_document(doc['document_id'], date, journal_id)
                    if path:
                        stored_paths.append(path)
                
                # Save metrics
                if self.metrics:
                    self.metrics.save_metrics()
                    self.metrics.record_debug_event('journal_processed', f"Date: {date_str}, Documents: {len(stored_paths)}")
                
                logger.debug(f"Finished scraping journal for date: {date_str}")
                return stored_paths
                
        except Exception as e:
            if self.metrics:
                self.metrics.record_debug_event('journal_processing_error', f"Date {date_str}: {str(e)}")
            logger.error(f"Failed to scrape journal for date {date}: {str(e)}")
            return []
