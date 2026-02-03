from fastapi import (
    FastAPI,
    HTTPException,
    BackgroundTasks,
    Query,
    UploadFile,
    File,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
import io
import os
import logging
import uuid
from pathlib import Path
from typing import List, Optional
from app.config import settings
from app.models import (
    SearchQuery,
    SearchResponse,
    ExportRequest,
    SummaryRequest,
    SummaryResponse,
)
from app.search.search_service import SearchService
from app.search.llm_service import LLMService
from app.export.exporter import DocumentExporter
from app.ingestion.indexer import DocumentIndexer
from app.ingestion.document_parser import DocumentParser
from app.utils.logging_config import setup_logging, set_correlation_id
from app.database import get_es_client, ElasticsearchClient
from sentence_transformers import SentenceTransformer

# Initialize structured logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Add correlation ID to each request for tracing"""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    set_correlation_id(correlation_id)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# Load AI Model (Shared)
logger.info(f"Loading shared AI model: {settings.EMBEDDING_MODEL_NAME}")
shared_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
logger.info("Shared model loaded successfully")

# Services
search_service = SearchService(shared_model)
llm_service = LLMService(shared_model)
exporter = DocumentExporter()
indexer = DocumentIndexer(shared_model)
parser = DocumentParser()

# Documents directory
DOCUMENTS_DIR = Path("/app/documents")
DOCUMENTS_DIR.mkdir(exist_ok=True)


@app.get("/")
async def root():
    return {
        "message": "Wood AI Internal Document Search API",
        "version": settings.VERSION,
    }


@app.get("/search", response_model=SearchResponse)
async def search_documents(
    query: str = Query(..., description="Search query"),
    limit: int = Query(20, description="Max results"),
):
    """Search documents by keyword (GET method)"""
    try:
        search_query = SearchQuery(query=query, limit=limit)
        return search_service.search(search_query)
    except ValueError as e:
        logger.warning(f"Invalid search query: {e}", extra={"query": query})
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Search error: {e}", extra={"query": query}, exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed")


@app.post("/search", response_model=SearchResponse)
async def search_documents_post(query: SearchQuery):
    """Search documents by keyword (POST method)"""
    try:
        return search_service.search(query)
    except ValueError as e:
        logger.warning(f"Invalid search query: {e}", extra={"query": query.query})
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Search error: {e}", extra={"query": query.query}, exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed")


@app.post("/summarize", response_model=SummaryResponse)
async def summarize_documents(request: SummaryRequest):
    """
    Generate AI summary for a query based on relevant documents.
    
    Fixed implementation:
    - Uses ES-stored content instead of synchronous file I/O
    - No blocking file operations in async endpoint
    - Proper error handling with specific exceptions
    - Eliminates bare except clauses
    """
    try:
        logger.info(
            "Generating summary",
            extra={"query": request.query}
        )
        
        # 1. Search for relevant documents
        search_query = SearchQuery(query=request.query, limit=5)
        search_results = search_service.search(search_query)

        if not search_results.results:
            logger.info(
                "No documents found for summary query",
                extra={"query": request.query}
            )
            return SummaryResponse(
                summary="No relevant documents found for your query. Please try different search terms.",
                query=request.query
            )

        # 2. Extract context from search results
        # Use ES-stored content instead of re-parsing files
        # The search results already contain snippets from ES
        context_docs = []
        
        # Get additional content from Elasticsearch for top 3 results
        es_client = get_es_client()
        top_results = search_results.results[:3]
        
        for result in top_results:
            try:
                # Fetch full document from ES to get more context
                doc = es_client.get(
                    index=settings.ELASTICSEARCH_INDEX,
                    id=result.id
                )
                
                if doc and '_source' in doc:
                    source = doc['_source']
                    # Combine relevant fields for context
                    context = {
                        'title': source.get('title', ''),
                        'background': source.get('background', ''),
                        'scope': source.get('scope', ''),
                        'content': source.get('content', '')[:1000],  # Limit to prevent token overflow
                    }
                    context_docs.append(context)
                    
            except Exception as e:
                logger.warning(
                    f"Failed to fetch document {result.id} from ES: {e}",
                    extra={"doc_id": result.id},
                    exc_info=True
                )
                # Use the snippet from search results as fallback
                context_docs.append({
                    'title': result.title,
                    'content': result.snippet
                })

        if not context_docs:
            logger.warning(
                "Failed to extract context from any documents",
                extra={"query": request.query}
            )
            return SummaryResponse(
                summary="Unable to generate summary due to document access issues.",
                query=request.query
            )

        # 3. Generate summary using LLM service
        summary = llm_service.generate_summary(request.query, context_docs)
        
        logger.info(
            "Summary generated successfully",
            extra={
                "query": request.query,
                "doc_count": len(context_docs),
                "summary_length": len(summary)
            }
        )
        
        return SummaryResponse(summary=summary, query=request.query)

    except ValueError as e:
        logger.warning(f"Invalid summary request: {e}", extra={"query": request.query})
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error generating summary: {e}",
            extra={"query": request.query},
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to generate summary. Please try again."
        )


def find_document_by_id(doc_id: str) -> Optional[Path]:
    """
    Find document file by various ID formats.
    
    Security: Validates doc_id to prevent path traversal attacks.
    """
    # Sanitize doc_id to prevent path traversal
    # Remove any path separators and parent directory references
    safe_doc_id = doc_id.replace('/', '').replace('\\\\', '').replace('..', '')
    
    # Only allow alphanumeric, hyphens, and underscores
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', safe_doc_id):
        logger.warning(
            f"Invalid document ID format",
            extra={"doc_id": doc_id, "sanitized": safe_doc_id}
        )
        return None
    
    # Try exact match first
    for ext in [".pdf", ".docx"]:
        doc_path = DOCUMENTS_DIR / f"{safe_doc_id}{ext}"
        if doc_path.exists() and doc_path.parent == DOCUMENTS_DIR:
            return doc_path

    # Try without extension if doc_id already has one
    doc_path = DOCUMENTS_DIR / safe_doc_id
    if doc_path.exists() and doc_path.parent == DOCUMENTS_DIR:
        return doc_path

    # Try fuzzy search - look for doc_id as substring
    try:
        for f in DOCUMENTS_DIR.glob("*.*"):
            if f.suffix in [".pdf", ".docx"]:
                # Check if doc_id matches stem or is contained in stem
                if safe_doc_id == f.stem or safe_doc_id in f.stem or f.stem in safe_doc_id:
                    # Verify file is actually in DOCUMENTS_DIR (no path traversal)
                    if f.parent == DOCUMENTS_DIR:
                        return f
    except Exception as e:
        logger.error(f"Error during document search: {e}", exc_info=True)

    return None


@app.get("/documents/{doc_id}/download")
async def download_document(doc_id: str):
    """Download a document by ID"""
    try:
        doc_path = find_document_by_id(doc_id)
        if not doc_path:
            raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

        return FileResponse(
            path=str(doc_path),
            media_type="application/pdf"
            if doc_path.suffix == ".pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=doc_path.name,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error downloading document: {e}",
            extra={"doc_id": doc_id},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to download document")


@app.get("/documents/{doc_id}/preview")
async def preview_document(doc_id: str):
    """Preview a document by ID (for inline display)"""
    try:
        doc_path = find_document_by_id(doc_id)
        if not doc_path:
            raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

        return FileResponse(
            path=str(doc_path),
            media_type="application/pdf"
            if doc_path.suffix == ".pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"inline; filename={doc_path.name}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error previewing document: {e}",
            extra={"doc_id": doc_id},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to preview document")


@app.post("/ingest")
async def ingest_documents(background_tasks: BackgroundTasks):
    """Ingest all documents from the documents directory"""
    try:
        pdf_files = list(DOCUMENTS_DIR.glob("*.pdf"))
        docx_files = list(DOCUMENTS_DIR.glob("*.docx"))
        all_files = pdf_files + docx_files

        if not all_files:
            return {"message": "No documents found", "count": 0}

        indexed_count = 0
        for file_path in all_files:
            try:
                parsed = parser.parse(str(file_path))
                if parsed:
                    indexer.index_document(
                        {
                            "id": file_path.stem,
                            "title": parsed.get("title", file_path.stem),
                            "content": parsed.get("content", ""),
                            "headings": parsed.get("headings", []),
                            "background": parsed.get("background", ""),
                            "file_path": str(file_path),
                            "file_type": file_path.suffix[1:],
                        }
                    )
                    indexed_count += 1
            except Exception as e:
                logger.error(
                    f"Error indexing file: {e}",
                    extra={"file_path": str(file_path)},
                    exc_info=True
                )

        logger.info(
            f"Ingestion completed",
            extra={"indexed": indexed_count, "total": len(all_files)}
        )
        
        return {"message": f"Indexed {indexed_count} documents", "count": indexed_count}
    except Exception as e:
        logger.error(f"Ingestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to ingest documents")


@app.post("/export")
async def export_documents(request: ExportRequest):
    """Export selected documents"""
    try:
        if request.format == "pdf":
            content = exporter.export_to_pdf(
                request.document_ids, request.include_summary
            )
            media_type = "application/pdf"
            filename = "wood_ai_documents.pdf"
        elif request.format == "docx":
            content = exporter.export_to_docx(
                request.document_ids, request.include_summary
            )
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = "wood_ai_documents.docx"
        else:
            content = exporter.export_to_csv(request.document_ids)
            media_type = "text/csv"
            filename = "wood_ai_documents.csv"

        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except ValueError as e:
        logger.warning(f"Invalid export request: {e}", extra={"format": request.format})
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Export error: {e}",
            extra={"format": request.format, "doc_count": len(request.document_ids)},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to export documents")


@app.get("/health")
async def health_check():
    """
    Health check endpoint with detailed system status.
    
    Uses centralized ES client for health verification.
    """
    health_status = {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "components": {
            "api": "healthy",
            "elasticsearch": "unknown",
            "model": "healthy",
        },
    }

    # Check Elasticsearch connectivity using centralized client
    try:
        es_client_instance = ElasticsearchClient()
        if es_client_instance.is_healthy():
            health_status["components"]["elasticsearch"] = "healthy"
        else:
            health_status["components"]["elasticsearch"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.warning(f"Elasticsearch health check failed: {e}", exc_info=True)
        health_status["components"]["elasticsearch"] = "unhealthy"
        health_status["status"] = "degraded"

    return health_status
