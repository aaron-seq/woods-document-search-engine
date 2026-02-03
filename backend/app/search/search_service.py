from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ElasticsearchException
from typing import List
import logging
from app.config import settings
from app.models import SearchQuery, SearchResult, SearchResponse
from app.database import get_es_client

logger = logging.getLogger(__name__)


class SearchService:
    """Handle document search queries with hybrid keyword + semantic search"""

    def __init__(self, model):
        """Initialize search service with embedding model.
        
        Args:
            model: SentenceTransformer model for generating embeddings
        """
        # Use centralized ES client with retry logic and connection pooling
        self.es = get_es_client()
        self.index_name = settings.ELASTICSEARCH_INDEX
        self.model = model
        logger.info(
            "SearchService initialized",
            extra={
                "index_name": self.index_name,
                "model_name": settings.EMBEDDING_MODEL_NAME
            }
        )

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for text"""
        try:
            return self.model.encode(text).tolist()
        except Exception as e:
            logger.error(
                f"Error generating embedding: {e}",
                extra={"text_length": len(text)},
                exc_info=True
            )
            raise

    def search(self, query: SearchQuery) -> SearchResponse:
        """Execute hybrid search query (keyword + semantic).
        
        Args:
            query: SearchQuery with search parameters
            
        Returns:
            SearchResponse with results and pagination info
        """
        # Use query field if keyword is empty
        search_term = query.keyword if query.keyword else query.query

        # 1. Keyword Search (BM25)
        must_queries = []
        if search_term and search_term.strip():
            must_queries.append(
                {
                    "multi_match": {
                        "query": search_term,
                        "fields": query.search_fields,
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                    }
                }
            )

        keyword_query = {
            "bool": {"must": must_queries if must_queries else [{"match_all": {}}]}
        }

        # 2. Semantic Search (KNN)
        knn_query = None
        if search_term and search_term.strip():
            try:
                query_vector = self._generate_embedding(search_term)
                knn_query = {
                    "field": "embedding",
                    "query_vector": query_vector,
                    "k": 10,
                    "num_candidates": 100,
                    "boost": 0.9,  # Give slightly less weight than exact keyword match
                }
            except Exception as e:
                logger.warning(
                    f"Failed to generate embedding for semantic search, falling back to keyword only: {e}",
                    extra={"search_term": search_term}
                )
                # Continue with keyword search only

        # Assemble ES Query
        es_body = {
            "query": keyword_query,
            "from": (query.page - 1) * query.page_size,
            "size": query.page_size,
            "sort": [{"_score": "desc"}],
            "highlight": {
                "fields": {field: {} for field in query.search_fields},
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],
            },
        }

        # Add KNN if available
        if knn_query:
            es_body["knn"] = knn_query

        try:
            logger.debug(
                "Executing search query",
                extra={
                    "search_term": search_term,
                    "page": query.page,
                    "page_size": query.page_size,
                    "has_knn": knn_query is not None
                }
            )
            
            response = self.es.search(index=self.index_name, body=es_body)

            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                highlights = hit.get("highlight", {})

                # Extract snippet from highlights, background, or content
                snippet = ""
                if highlights:
                    snippet = list(highlights.values())[0][0][:200]
                elif source.get("background"):
                    snippet = source["background"][:200]
                elif source.get("content"):
                    snippet = source["content"][:200]

                results.append(
                    SearchResult(
                        id=source["id"],
                        title=source["title"],
                        snippet=snippet,
                        file_path=source["file_path"],
                        file_type=source.get("file_type", "pdf"),
                        download_url=f"/documents/{source['id']}/download",
                        score=hit["_score"],
                        highlights=highlights,
                    )
                )

            total_hits = response["hits"]["total"]["value"]
            logger.info(
                "Search completed successfully",
                extra={
                    "search_term": search_term,
                    "total_results": total_hits,
                    "returned_results": len(results)
                }
            )

            return SearchResponse(
                total=total_hits,
                page=query.page,
                page_size=query.page_size,
                results=results,
            )

        except ElasticsearchException as e:
            logger.error(
                f"Elasticsearch error during search: {e}",
                extra={
                    "search_term": search_term,
                    "index": self.index_name,
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            # Return empty results instead of raising
            return SearchResponse(
                total=0, page=query.page, page_size=query.page_size, results=[]
            )
        except Exception as e:
            logger.error(
                f"Unexpected error during search: {e}",
                extra={"search_term": search_term},
                exc_info=True
            )
            return SearchResponse(
                total=0, page=query.page, page_size=query.page_size, results=[]
            )
