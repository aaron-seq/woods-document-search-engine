from elasticsearch import Elasticsearch
from typing import List
from app.config import settings
from app.models import SearchQuery, SearchResult, SearchResponse


class SearchService:
    """Handle document search queries"""

    def __init__(self, model):
        self.es = Elasticsearch(
            [f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"]
        )
        self.index_name = settings.ELASTICSEARCH_INDEX
        self.model = model

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for text"""
        return self.model.encode(text).tolist()

    def search(self, query: SearchQuery) -> SearchResponse:
        """Execute search query with Hybrid Search"""
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
            query_vector = self._generate_embedding(search_term)
            knn_query = {
                "field": "embedding",
                "query_vector": query_vector,
                "k": 10,
                "num_candidates": 100,
                "boost": 0.9,  # Give slightly less weight than exact keyword match
            }

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
            response = self.es.search(index=self.index_name, body=es_body)

            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                highlights = hit.get("highlight", {})

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

            return SearchResponse(
                total=response["hits"]["total"]["value"],
                page=query.page,
                page_size=query.page_size,
                results=results,
            )

        except Exception as e:
            print(f"Search error: {e}")
            return SearchResponse(
                total=0, page=query.page, page_size=query.page_size, results=[]
            )
