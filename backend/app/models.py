from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Document(BaseModel):
    """Document model for indexing"""

    id: str
    title: str
    file_path: str
    file_type: str
    headings: List[str] = []
    background: Optional[str] = None
    scope: Optional[str] = None
    content: Optional[str] = None
    embedding: Optional[List[float]] = None  # Vector embedding for semantic search
    category: Optional[str] = None  # For future AI categorization
    created_at: datetime
    updated_at: datetime


class SearchQuery(BaseModel):
    """Search query parameters"""

    query: str = ""
    keyword: str = ""
    search_fields: List[str] = ["title", "headings", "background", "scope", "content"]
    page: int = 1
    page_size: int = 20
    limit: int = 20


class SearchResult(BaseModel):
    """Individual search result"""

    id: str
    title: str
    snippet: str
    file_path: str
    file_type: str = "pdf"
    download_url: str = ""
    score: float
    highlights: dict = {}


class SearchResponse(BaseModel):
    """Search response with pagination"""

    total: int
    page: int
    page_size: int
    results: List[SearchResult]


class ExportRequest(BaseModel):
    """Export request parameters"""

    document_ids: List[str]
    format: str = "pdf"  # pdf, docx, csv
    include_summary: bool = False


class SummaryRequest(BaseModel):
    """Request for AI summary"""

    query: str


class SummaryResponse(BaseModel):
    """AI summary response"""

    summary: str
    query: str
