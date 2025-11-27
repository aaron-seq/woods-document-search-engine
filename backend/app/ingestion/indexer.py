from elasticsearch import Elasticsearch
from typing import Dict
import hashlib
import os
from pathlib import Path
from app.config import settings
from app.ingestion.document_parser import DocumentParser

class DocumentIndexer:
    """Index documents into Elasticsearch"""
    
    def __init__(self):
        self.es = Elasticsearch([f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"])
        self.index_name = settings.ELASTICSEARCH_INDEX
        self._create_index()
    
    def _create_index(self):
        """Create Elasticsearch index with proper mappings"""
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
                        "category": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"}
                    }
                }
            }
            self.es.indices.create(index=self.index_name, body=mappings)
            print(f"Created index: {self.index_name}")
    
    def _generate_doc_id(self, file_path: str) -> str:
        """Generate document ID from filename (not hash)"""
        # Use the filename without extension as ID
        return Path(file_path).stem
    
    def index_document(self, doc_data: Dict) -> bool:
        """Index a single document"""
        try:
            # Use the provided ID or generate from file path
            doc_id = doc_data.get('id') or self._generate_doc_id(doc_data['file_path'])
            doc_data['id'] = doc_id
            self.es.index(index=self.index_name, id=doc_id, document=doc_data)
            print(f"Indexed document with ID: {doc_id}")
            return True
        except Exception as e:
            print(f"Error indexing document: {e}")
            return False
    
    def index_directory(self, directory_path: str) -> Dict:
        """Index all documents in a directory"""
        results = {'success': 0, 'failed': 0, 'skipped': 0}
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                doc_data = DocumentParser.parse_document(file_path)
                if doc_data:
                    if self.index_document(doc_data):
                        results['success'] += 1
                        print(f"Indexed: {file}")
                    else:
                        results['failed'] += 1
                else:
                    results['skipped'] += 1
        return results
    
    def delete_all(self):
        """Delete all documents from index"""
        try:
            self.es.delete_by_query(index=self.index_name, body={"query": {"match_all": {}}})
            print(f"Deleted all documents from {self.index_name}")
        except Exception as e:
            print(f"Error deleting documents: {e}")
