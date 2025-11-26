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
    category: Optional[str] = None  # For future AI categorization
    created_at: datetime
    updated_at: datetime

class SearchQuery(BaseModel):
    """Search query parameters"""
    keyword: str
    search_fields: List[str] = ["title", "headings", "background", "scope"]
    page: int = 1
    page_size: int = 20

class SearchResult(BaseModel):
    """Individual search result"""
    id: str
    title: str
    snippet: str
    file_path: str
    score: float
    highlights: dict = {}

class SearchResponse(BaseModel):
    """Search response with pagination"""
    total: int
    page: int
    page_size: int
    results: List[SearchResult]

class ExportRequest(BaseModel):
    """Export request model"""
    document_ids: List[str]
    format: str = "pdf"  # pdf, docx, csv
    include_summary: bool = False  # For future AI summary generation
