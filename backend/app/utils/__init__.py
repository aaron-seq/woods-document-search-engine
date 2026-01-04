"""
Utility functions for Woods Document Search Engine.

This module exports commonly used utilities:
- ElasticsearchClientManager: Singleton ES client with retry logic
- get_elasticsearch_client: Get ES client instance
- setup_logging: Configure structured logging
- get_logger: Get logger instance
- set_correlation_id: Set request correlation ID
- get_correlation_id: Get current correlation ID
"""

from app.utils.elasticsearch_client import (
    ElasticsearchClientManager,
    es_client_manager,
    get_elasticsearch_client,
)
from app.utils.logging_config import (
    setup_logging,
    get_logger,
    set_correlation_id,
    get_correlation_id,
    correlation_id,
)

__all__ = [
    # Elasticsearch
    "ElasticsearchClientManager",
    "es_client_manager",
    "get_elasticsearch_client",
    # Logging
    "setup_logging",
    "get_logger",
    "set_correlation_id",
    "get_correlation_id",
    "correlation_id",
]
