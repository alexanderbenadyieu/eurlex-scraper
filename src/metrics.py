"""Metrics collection for EUR-Lex scraper."""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram, write_to_textfile
from prometheus_client.core import CollectorRegistry
from loguru import logger


class MetricsCollector:
    """Collects and exports metrics for the scraper."""
    
    def __init__(self, metrics_dir: Optional[str] = None, export_port: Optional[int] = None):
        """
        Initialize metrics collector.
        
        Args:
            metrics_dir: Directory to store metrics files
            export_port: Optional port to export metrics via HTTP
        """
        self.registry = CollectorRegistry()
        self.metrics_dir = Path(metrics_dir) if metrics_dir else Path("metrics")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        # Document processing metrics
        self.documents_processed = Counter(
            'eurlex_documents_processed_total',
            'Total number of documents processed',
            ['status', 'date'],  # success/failure, processing date
            registry=self.registry
        )
        
        # Request metrics
        self.requests_total = Counter(
            'eurlex_requests_total',
            'Total number of HTTP requests made',
            ['status', 'url'],  # success/failure, URL
            registry=self.registry
        )
        
        self.retry_attempts = Counter(
            'eurlex_retry_attempts_total',
            'Total number of retry attempts',
            ['url'],  # URL that needed retry
            registry=self.registry
        )
        
        # Processing time metrics
        self.document_processing_time = Histogram(
            'eurlex_document_processing_seconds',
            'Time spent processing documents',
            ['doc_id'],  # Document ID
            buckets=(1, 2, 5, 10, 30, 60, 120),
            registry=self.registry
        )
        
        self.journal_processing_time = Histogram(
            'eurlex_journal_processing_seconds',
            'Time spent processing journals',
            ['date'],  # Journal date
            buckets=(10, 30, 60, 120, 300, 600),
            registry=self.registry
        )
        
        # Storage metrics
        self.storage_size = Gauge(
            'eurlex_storage_size_bytes',
            'Total size of stored documents',
            registry=self.registry
        )
        
        # Validation metrics
        self.validation_errors = Counter(
            'eurlex_validation_errors_total',
            'Total number of validation errors',
            ['type', 'details'],  # error type, error details
            registry=self.registry
        )
        
        # Debug metrics
        self.debug_events = Counter(
            'eurlex_debug_events_total',
            'Debug events for troubleshooting',
            ['event_type', 'details'],
            registry=self.registry
        )
    
    def save_metrics(self) -> None:
        """Save metrics to local files."""
        try:
            # Save Prometheus format metrics
            prom_file = self.metrics_dir / f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.prom"
            write_to_textfile(str(prom_file), self.registry)
            
            # Save JSON format for easier reading
            metrics_dict = {
                'documents_processed': {
                    'success': self.documents_processed.labels(status='success', date='*')._value.get(),
                    'failure': self.documents_processed.labels(status='failure', date='*')._value.get()
                },
                'requests': {
                    'success': sum(self.requests_total.labels(status='success', url='*')._value.get() for _ in [0]),
                    'failure': sum(self.requests_total.labels(status='failure', url='*')._value.get() for _ in [0])
                },
                'retry_attempts': sum(self.retry_attempts.labels(url='*')._value.get() for _ in [0]),
                'validation_errors': sum(self.validation_errors.labels(type='*', details='*')._value.get() for _ in [0])
            }
            
            json_file = self.metrics_dir / f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(json_file, 'w') as f:
                json.dump(metrics_dict, f, indent=2)
            
            logger.info(f"Metrics saved to {self.metrics_dir}")
            
        except Exception as e:
            logger.error(f"Failed to save metrics: {str(e)}")
    
    def record_document_processed(self, success: bool = True, date: str = '') -> None:
        """Record a processed document."""
        status = 'success' if success else 'failure'
        self.documents_processed.labels(status=status, date=date).inc()
    
    def record_request(self, success: bool = True, url: str = '') -> None:
        """Record an HTTP request."""
        status = 'success' if success else 'failure'
        self.requests_total.labels(status=status, url=url).inc()
    
    def record_retry_attempt(self, url: str = '') -> None:
        """Record a retry attempt."""
        self.retry_attempts.labels(url=url).inc()
    
    def record_validation_error(self, error_type: str, details: str = '') -> None:
        """Record a validation error."""
        self.validation_errors.labels(type=error_type, details=details).inc()
    
    def record_debug_event(self, event_type: str, details: str = '') -> None:
        """Record a debug event."""
        self.debug_events.labels(event_type=event_type, details=details).inc()
    
    def update_storage_size(self, base_dir: Path) -> None:
        """Update total storage size."""
        total_size = sum(f.stat().st_size for f in base_dir.rglob('*') if f.is_file())
        self.storage_size.set(total_size)
    
    def time_document_processing(self, doc_id: str = ''):
        """Context manager for timing document processing."""
        return self.document_processing_time.labels(doc_id=doc_id).time()
    
    def time_journal_processing(self, date: str = ''):
        """Context manager for timing journal processing."""
        return self.journal_processing_time.labels(date=date).time()
