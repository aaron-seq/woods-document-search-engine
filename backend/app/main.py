from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
from app.config import settings
from app.models import SearchQuery, SearchResponse, ExportRequest
from app.search.search_service import SearchService
from app.export.exporter import DocumentExporter
from app.ingestion.indexer import DocumentIndexer

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
search_service = SearchService()
exporter = DocumentExporter()
indexer = DocumentIndexer()

@app.get("/")
async def root():
    return {"message": "Woods Document Search API", "version": settings.VERSION}

@app.post("/search", response_model=SearchResponse)
async def search_documents(query: SearchQuery):
    """Search documents by keyword"""
    try:
        return search_service.search(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export")
async def export_documents(request: ExportRequest):
    """Export selected documents"""
    try:
        if request.format == "pdf":
            content = exporter.export_to_pdf(request.document_ids, request.include_summary)
            media_type = "application/pdf"
            filename = "woods_documents.pdf"
        elif request.format == "docx":
            content = exporter.export_to_docx(request.document_ids, request.include_summary)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = "woods_documents.docx"
        elif request.format == "csv":
            content = exporter.export_to_csv(request.document_ids)
            media_type = "text/csv"
            filename = "woods_documents.csv"
        else:
            raise HTTPException(status_code=400, detail="Invalid format")
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/reindex")
async def reindex_documents(background_tasks: BackgroundTasks):
    """Reindex all documents (admin only)"""
    def reindex():
        indexer.delete_all()
        results = indexer.index_directory(settings.DOCUMENTS_PATH)
        print(f"Reindexing complete: {results}")
    background_tasks.add_task(reindex)
    return {"message": "Reindexing started in background"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
