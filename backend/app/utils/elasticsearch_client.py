from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, ConnectionTimeout
import time
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class ElasticsearchClientManager:
    """Manage Elasticsearch client with connection pooling and retry logic"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_client(self) -> Elasticsearch:
        """Get or create Elasticsearch client with retry logic"""
        if self._client is None:
            self._client = self._create_client_with_retry()
        
        # Verify connection is still alive
        try:
            if not self._client.ping():
                logger.warning("Elasticsearch connection lost, reconnecting...")
                self._client = self._create_client_with_retry()
        except Exception as e:
            logger.error(f"Elasticsearch ping failed: {e}", exc_info=True)
            self._client = self._create_client_with_retry()
        
        return self._client
    
    def _create_client_with_retry(self, max_retries=None, retry_delay=None) -> Elasticsearch:
        """Create Elasticsearch client with exponential backoff retry logic"""
        max_retries = max_retries or settings.ELASTICSEARCH_MAX_RETRIES
        retry_delay = retry_delay or settings.ELASTICSEARCH_RETRY_DELAY
        
        es_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"
        
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Attempting to connect to Elasticsearch at {es_url}",
                    extra={"attempt": attempt + 1, "max_retries": max_retries}
                )
                
                client = Elasticsearch(
                    [es_url],
                    request_timeout=settings.ELASTICSEARCH_TIMEOUT,
                    max_retries=3,
                    retry_on_timeout=True
                )
                
                # Verify connection
                if client.ping():
                    logger.info(
                        "Successfully connected to Elasticsearch",
                        extra={"host": settings.ELASTICSEARCH_HOST, "port": settings.ELASTICSEARCH_PORT}
                    )
                    return client
                else:
                    logger.warning(f"Elasticsearch ping failed on attempt {attempt + 1}")
                    
            except (ConnectionError, ConnectionTimeout) as e:
                logger.warning(
                    f"Elasticsearch connection failed on attempt {attempt + 1}",
                    extra={"error": str(e), "attempt": attempt + 1}
                )
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(
                        "Failed to connect to Elasticsearch after all retries",
                        extra={"max_retries": max_retries}
                    )
                    raise ConnectionError(
                        f"Failed to connect to Elasticsearch at {es_url} after {max_retries} attempts"
                    )
            except Exception as e:
                logger.error(f"Unexpected error connecting to Elasticsearch: {e}", exc_info=True)
                raise
        
        raise ConnectionError(f"Failed to connect to Elasticsearch at {es_url}")
    
    def close(self):
        """Close Elasticsearch client connection"""
        if self._client is not None:
            try:
                self._client.close()
                logger.info("Elasticsearch client closed")
            except Exception as e:
                logger.error(f"Error closing Elasticsearch client: {e}", exc_info=True)
            finally:
                self._client = None


# Singleton instance
es_client_manager = ElasticsearchClientManager()


def get_elasticsearch_client() -> Elasticsearch:
    """Get Elasticsearch client instance"""
    return es_client_manager.get_client()
