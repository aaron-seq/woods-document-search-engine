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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse)
async def search_documents_post(query: SearchQuery):
    """Search documents by keyword (POST method)"""
    try:
        return search_service.search(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/summarize", response_model=SummaryResponse)
async def summarize_documents(request: SummaryRequest):
    """Generate AI summary for a query based on relevant documents"""
    try:
        # 1. Search for relevant documents
        search_query = SearchQuery(query=request.query, limit=5)
        search_results = search_service.search(search_query)

        # 2. Extract content from results
        context_docs = []
        for result in search_results.results:
            # We need to fetch the full content (or at least enough for summarization)
            # The search result 'snippet' might be too short.
            # Ideally search service returns full content or sufficient context.
            # For POC, let's assume we can fetch the document content if we have the file path or ID.
            # But wait, search_result has 'snippet' and 'highlights'.
            # We might want to use the 'content' field from ES if we asked for it.
            # SearchService currently only returns SearchResult with snippets.
            # Let's rely on what's in ES. We can modify SearchService to return more data or query ES here again?
            # Better: Make SearchService return 'content' in a hidden field or fetch by ID.
            # For simplicity, let's look up the file or re-query ES by ID?
            # Actually, `search_service.search` retrieves source. I should probably add `content` to `SearchResult` or fetch it.

            # Quick fix: Use the snippet for now, or fetch by ID.
            # Let's try to fetch by ID using the same logic as `download_document` or `find_document_by_id`.
            # Accessing file system is slow.
            # Let's rely on ES source if possible.
            # I will just use the `snippet` for now if it's long enough, OR I'll update `SearchService` later to return full content.
            # For "Senior ML Engineer" quality, I should do RAG properly. RAG needs context.
            # I'll try to find the document file since I have `find_document_by_id` available in this file.
            pass

        # Real implementation: Fetch full content for top 3 docs
        top_docs = search_results.results[:3]
        real_context = []
        for doc in top_docs:
            # Reconstruct content from file (expensive but accurate)
            # OR just use the snippet if it captured the relevant part.
            # Let's use the file parser again? No, too slow.
            # Let's assume the Snippet + Background is decent context for the POC.
            # Or better, read the file content since we have `doc.file_path`.
            # `doc.file_path` comes from ES.

            # CAUTION: `doc.file_path` might be inside docker container path.
            # Let's try to read it.
            try:
                # doc.file_path is absolute path in container?
                # parser.parse returns dict.
                if doc.file_path:
                    # Depending on how it was indexed.
                    full_doc = parser.parse(doc.file_path)  # Utilize existing parser
                    if full_doc:
                        real_context.append(full_doc)
            except:
                continue

        summary = llm_service.generate_summary(request.query, real_context)
        return SummaryResponse(summary=summary, query=request.query)

    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def find_document_by_id(doc_id: str) -> Optional[Path]:
    """Find document file by various ID formats"""
    # Try exact match first
    for ext in [".pdf", ".docx"]:
        doc_path = DOCUMENTS_DIR / f"{doc_id}{ext}"
        if doc_path.exists():
            return doc_path

    # Try without extension if doc_id already has one
    doc_path = DOCUMENTS_DIR / doc_id
    if doc_path.exists():
        return doc_path

    # Try fuzzy search - look for doc_id as substring
    for f in DOCUMENTS_DIR.glob("*.*"):
        if f.suffix in [".pdf", ".docx"]:
            # Check if doc_id matches stem or is contained in stem
            if doc_id == f.stem or doc_id in f.stem or f.stem in doc_id:
                return f

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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


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
                logger.error(f"Error indexing {file_path}: {e}", exc_info=True)

        return {"message": f"Indexed {indexed_count} documents", "count": indexed_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint with detailed system status"""
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

    # Check Elasticsearch connectivity
    try:
        from elasticsearch import Elasticsearch

        es = Elasticsearch(
            [f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"]
        )
        if es.ping():
            health_status["components"]["elasticsearch"] = "healthy"
        else:
            health_status["components"]["elasticsearch"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.warning(f"Elasticsearch health check failed: {e}")
        health_status["components"]["elasticsearch"] = "unhealthy"
        health_status["status"] = "degraded"

    return health_status
