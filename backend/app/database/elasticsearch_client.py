from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError, TransportError
import time
import logging
from app.config import settings
from typing import Optional

logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """
    Singleton Elasticsearch client with connection pooling, retry logic,
    and health verification.
    
    Addresses issues:
    - #2: Missing error handling causes ES connection failure on startup
    - #14: Missing ES connection error handling and retry logic
    
    Features:
    - Singleton pattern ensures single client instance per application
    - Automatic retry with exponential backoff
    - Connection health verification before returning client
    - Proper exception handling with detailed logging
    """
    
    _instance: Optional['ElasticsearchClient'] = None
    _client: Optional[Elasticsearch] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_client(self) -> Elasticsearch:
        """
        Get Elasticsearch client instance with connection verification.
        
        Returns:
            Elasticsearch: Active ES client instance
            
        Raises:
            ConnectionError: If unable to connect after max retries
        """
        if self._client is None:
            self._client = self._initialize_client()
        
        # Verify connection is still alive
        try:
            if not self._client.ping():
                logger.warning("ES client ping failed, reinitializing connection")
                self._client = self._initialize_client()
        except Exception as e:
            logger.error(f"ES ping check failed: {e}, reinitializing", exc_info=True)
            self._client = self._initialize_client()
        
        return self._client
    
    def _initialize_client(self) -> Elasticsearch:
        """
        Initialize Elasticsearch client with retry logic.
        
        Returns:
            Elasticsearch: Initialized client instance
            
        Raises:
            ConnectionError: If max retries exceeded
        """
        es_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"
        
        for attempt in range(settings.ELASTICSEARCH_MAX_RETRIES):
            try:
                logger.info(
                    f"Attempting ES connection (attempt {attempt + 1}/{settings.ELASTICSEARCH_MAX_RETRIES})",
                    extra={"elasticsearch_url": es_url}
                )
                
                client = Elasticsearch(
                    [es_url],
                    timeout=settings.ELASTICSEARCH_TIMEOUT,
                    max_retries=3,
                    retry_on_timeout=True,
                    # Connection pooling settings
                    maxsize=25,
                )
                
                # Verify connection with ping
                if client.ping():
                    logger.info(
                        "Successfully connected to Elasticsearch",
                        extra={
                            "elasticsearch_url": es_url,
                            "attempt": attempt + 1
                        }
                    )
                    return client
                else:
                    logger.warning(
                        f"ES ping failed on attempt {attempt + 1}",
                        extra={"elasticsearch_url": es_url}
                    )
                    
            except (ESConnectionError, TransportError) as e:
                logger.warning(
                    f"ES connection attempt {attempt + 1}/{settings.ELASTICSEARCH_MAX_RETRIES} failed",
                    extra={
                        "elasticsearch_url": es_url,
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                
                if attempt < settings.ELASTICSEARCH_MAX_RETRIES - 1:
                    delay = settings.ELASTICSEARCH_RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Failed to connect to Elasticsearch after {settings.ELASTICSEARCH_MAX_RETRIES} attempts",
                        extra={"elasticsearch_url": es_url}
                    )
                    raise ConnectionError(
                        f"Failed to connect to Elasticsearch at {es_url} "
                        f"after {settings.ELASTICSEARCH_MAX_RETRIES} attempts. "
                        f"Last error: {str(e)}"
                    )
            
            except Exception as e:
                logger.error(
                    f"Unexpected error during ES connection attempt {attempt + 1}",
                    extra={
                        "elasticsearch_url": es_url,
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                raise
        
        raise ConnectionError(
            f"Failed to establish Elasticsearch connection to {es_url} "
            f"after {settings.ELASTICSEARCH_MAX_RETRIES} attempts"
        )
    
    def is_healthy(self) -> bool:
        """
        Check if Elasticsearch connection is healthy.
        
        Returns:
            bool: True if ES is reachable and healthy
        """
        try:
            if self._client is None:
                return False
            return self._client.ping()
        except Exception as e:
            logger.warning(f"ES health check failed: {e}")
            return False
    
    def close(self):
        """Close the Elasticsearch client connection."""
        if self._client is not None:
            try:
                self._client.close()
                logger.info("Elasticsearch client connection closed")
            except Exception as e:
                logger.error(f"Error closing ES client: {e}", exc_info=True)
            finally:
                self._client = None


# Module-level function for easy access
def get_es_client() -> Elasticsearch:
    """
    Get the singleton Elasticsearch client instance.
    
    Returns:
        Elasticsearch: Active ES client
        
    Example:
        >>> from app.database import get_es_client
        >>> es = get_es_client()
        >>> es.search(index="my_index", body={"query": {"match_all": {}}})
    """
    return ElasticsearchClient().get_client()
