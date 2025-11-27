from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
import io
import os
from pathlib import Path
from typing import List, Optional
from app.config import settings
from app.models import SearchQuery, SearchResponse, ExportRequest
from app.search.search_service import SearchService
from app.export.exporter import DocumentExporter
from app.ingestion.indexer import DocumentIndexer
from app.ingestion.document_parser import DocumentParser

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
parser = DocumentParser()

# Documents directory
DOCUMENTS_DIR = Path("/app/documents")
DOCUMENTS_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {"message": "Wood AI Internal Document Search API", "version": settings.VERSION}

@app.get("/search", response_model=SearchResponse)
async def search_documents(
    query: str = Query(..., description="Search query"),
    limit: int = Query(20, description="Max results")
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

def find_document_by_id(doc_id: str) -> Optional[Path]:
    """Find document file by various ID formats"""
    # Try exact match first
    for ext in ['.pdf', '.docx']:
        doc_path = DOCUMENTS_DIR / f"{doc_id}{ext}"
        if doc_path.exists():
            return doc_path
    
    # Try without extension if doc_id already has one
    doc_path = DOCUMENTS_DIR / doc_id
    if doc_path.exists():
        return doc_path
    
    # Try fuzzy search - look for doc_id as substring
    for f in DOCUMENTS_DIR.glob("*.*"):
        if f.suffix in ['.pdf', '.docx']:
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
            media_type="application/pdf" if doc_path.suffix == '.pdf' else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=doc_path.name
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
            media_type="application/pdf" if doc_path.suffix == '.pdf' else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"inline; filename={doc_path.name}"}
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
                    indexer.index_document({
                        "id": file_path.stem,
                        "title": parsed.get("title", file_path.stem),
                        "content": parsed.get("content", ""),
                        "headings": parsed.get("headings", []),
                        "background": parsed.get("background", ""),
                        "file_path": str(file_path),
                        "file_type": file_path.suffix[1:]
                    })
                    indexed_count += 1
            except Exception as e:
                print(f"Error indexing {file_path}: {e}")
        
        return {"message": f"Indexed {indexed_count} documents", "count": indexed_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export")
async def export_documents(request: ExportRequest):
    """Export selected documents"""
    try:
        if request.format == "pdf":
            content = exporter.export_to_pdf(request.document_ids, request.include_summary)
            media_type = "application/pdf"
            filename = "wood_ai_documents.pdf"
        elif request.format == "docx":
            content = exporter.export_to_docx(request.document_ids, request.include_summary)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = "wood_ai_documents.docx"
        else:
            content = exporter.export_to_csv(request.document_ids)
            media_type = "text/csv"
            filename = "wood_ai_documents.csv"
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
