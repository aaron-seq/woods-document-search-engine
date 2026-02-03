from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ElasticsearchException
from typing import Dict, List
import hashlib
import os
import logging
from pathlib import Path
from app.config import settings
from app.ingestion.document_parser import DocumentParser
from app.database import get_es_client

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Index documents into Elasticsearch with proper error handling"""

    def __init__(self, model):
        """Initialize document indexer.
        
        Args:
            model: SentenceTransformer model for generating embeddings
        """
        # Use centralized ES client with retry logic
        self.es = get_es_client()
        self.index_name = settings.ELASTICSEARCH_INDEX
        self.model = model
        self._create_index()
        logger.info(
            "DocumentIndexer initialized",
            extra={
                "index_name": self.index_name,
                "model_name": settings.EMBEDDING_MODEL_NAME
            }
        )

    def _create_index(self):
        """Create Elasticsearch index with proper mappings if it doesn't exist"""
        try:
            if not self.es.indices.exists(index=self.index_name):
                mappings = {
                    "mappings": {
                        "properties": {
                            "id": {"type": "keyword"},
                            "title": {"type": "text", "analyzer": "standard"},
                            "file_path": {"type": "keyword"},
                            "file_type": {"type": "keyword"},
                            "headings": {"type": "text", "analyzer": "standard"},
                            "background": {"type": "text", "analyzer": "standard"},
                            "scope": {"type": "text", "analyzer": "standard"},
                            "content": {"type": "text", "analyzer": "standard"},
                            "embedding": {
                                "type": "dense_vector",
                                "dims": settings.EMBEDDING_DIMENSION,
                                "index": True,
                                "similarity": "cosine",
                            },
                            "category": {"type": "keyword"},
                            "created_at": {"type": "date"},
                            "updated_at": {"type": "date"},
                        }
                    }
                }
                self.es.indices.create(index=self.index_name, body=mappings)
                logger.info(
                    f"Created Elasticsearch index",
                    extra={"index_name": self.index_name}
                )
            else:
                logger.info(
                    f"Elasticsearch index already exists",
                    extra={"index_name": self.index_name}
                )
        except ElasticsearchException as e:
            logger.error(
                f"Failed to create Elasticsearch index: {e}",
                extra={
                    "index_name": self.index_name,
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            raise

    def _generate_doc_id(self, file_path: str) -> str:
        """Generate document ID from filename (not hash)"""
        # Use the filename without extension as ID
        return Path(file_path).stem

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for text.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List[float]: Vector embedding
        """
        try:
            return self.model.encode(text).tolist()
        except Exception as e:
            logger.error(
                f"Error generating embedding: {e}",
                extra={"text_length": len(text)},
                exc_info=True
            )
            raise

    def index_document(self, doc_data: Dict) -> bool:
        """Index a single document.
        
        Args:
            doc_data: Dictionary containing document data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Use the provided ID or generate from file path
            doc_id = doc_data.get("id") or self._generate_doc_id(doc_data["file_path"])
            doc_data["id"] = doc_id

            # Generate embedding
            # Combine important fields for embedding: Title > Background > Scope > Content (truncated)
            text_to_embed = f"{doc_data.get('title', '')} {doc_data.get('background', '')} {doc_data.get('scope', '')} {doc_data.get('content', '')[:1000]}"
            
            try:
                doc_data["embedding"] = self._generate_embedding(text_to_embed)
            except Exception as e:
                logger.warning(
                    f"Failed to generate embedding for document {doc_id}, indexing without embedding: {e}",
                    extra={"doc_id": doc_id}
                )
                # Continue without embedding
                doc_data["embedding"] = None

            self.es.index(index=self.index_name, id=doc_id, document=doc_data)
            logger.info(
                f"Successfully indexed document",
                extra={
                    "doc_id": doc_id,
                    "title": doc_data.get('title', 'N/A'),
                    "file_type": doc_data.get('file_type', 'unknown')
                }
            )
            return True
            
        except ElasticsearchException as e:
            logger.error(
                f"Elasticsearch error indexing document: {e}",
                extra={
                    "doc_id": doc_data.get('id', 'unknown'),
                    "file_path": doc_data.get('file_path', 'unknown'),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error indexing document: {e}",
                extra={
                    "doc_id": doc_data.get('id', 'unknown'),
                    "file_path": doc_data.get('file_path', 'unknown')
                },
                exc_info=True
            )
            return False

    def index_directory(self, directory_path: str) -> Dict:
        """Index all documents in a directory.
        
        Args:
            directory_path: Path to directory containing documents
            
        Returns:
            Dict with counts of successful, failed, and skipped documents
        """
        results = {"success": 0, "failed": 0, "skipped": 0}
        
        logger.info(
            f"Starting directory indexing",
            extra={"directory_path": directory_path}
        )
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    doc_data = DocumentParser.parse_document(file_path)
                    if doc_data:
                        if self.index_document(doc_data):
                            results["success"] += 1
                        else:
                            results["failed"] += 1
                    else:
                        results["skipped"] += 1
                        logger.debug(
                            f"Skipped file (unsupported or empty)",
                            extra={"file_path": file_path}
                        )
                except Exception as e:
                    results["failed"] += 1
                    logger.error(
                        f"Error processing file: {e}",
                        extra={"file_path": file_path},
                        exc_info=True
                    )
        
        logger.info(
            f"Directory indexing completed",
            extra={
                "directory_path": directory_path,
                "success": results["success"],
                "failed": results["failed"],
                "skipped": results["skipped"]
            }
        )
        
        return results

    def delete_all(self):
        """Delete all documents from index"""
        try:
            response = self.es.delete_by_query(
                index=self.index_name, 
                body={"query": {"match_all": {}}}
            )
            deleted_count = response.get('deleted', 0)
            logger.info(
                f"Deleted all documents from index",
                extra={
                    "index_name": self.index_name,
                    "deleted_count": deleted_count
                }
            )
        except ElasticsearchException as e:
            logger.error(
                f"Error deleting documents: {e}",
                extra={
                    "index_name": self.index_name,
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            raise
