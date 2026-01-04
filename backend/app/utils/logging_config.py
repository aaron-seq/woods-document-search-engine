import logging
import sys
from pythonjsonlogger import jsonlogger
from app.config import settings
import uuid
from contextvars import ContextVar

# Context variable for correlation ID tracking
correlation_id: ContextVar[str] = ContextVar('correlation_id', default=None)


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records"""
    
    def filter(self, record):
        record.correlation_id = correlation_id.get() or 'N/A'
        return True


def setup_logging():
    """Configure structured logging for the application"""
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Configure formatter based on format setting
    if settings.LOG_FORMAT == "json":
        # JSON formatter for production
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(correlation_id)s %(message)s',
            rename_fields={
                'asctime': 'timestamp',
                'name': 'logger',
                'levelname': 'level',
            }
        )
    else:
        # Text formatter for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    
    # Add correlation ID filter
    handler.addFilter(CorrelationIdFilter())
    
    # Add handler to logger
    logger.addHandler(handler)
    
    # Configure third-party loggers
    logging.getLogger('elasticsearch').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sentence_transformers').setLevel(logging.INFO)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)


def set_correlation_id(request_id: str = None) -> str:
    """Set correlation ID for the current request"""
    if request_id is None:
        request_id = str(uuid.uuid4())
    correlation_id.set(request_id)
    return request_id


def get_correlation_id() -> str:
    """Get current correlation ID"""
    return correlation_id.get()
