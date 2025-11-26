"""Document ingestion module for parsing and indexing documents."""

from .document_parser import DocumentParser
from .indexer import DocumentIndexer

__all__ = ["DocumentParser", "DocumentIndexer"]
