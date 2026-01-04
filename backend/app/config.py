from pydantic import field_validator, Field
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application configuration settings with validation"""

    APP_NAME: str = "Wood AI Internal Document Search Engine"
    VERSION: str = "1.0.0"
    
    # Environment
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")

    # Elasticsearch - Required in production
    ELASTICSEARCH_HOST: str = Field(..., min_length=1)
    ELASTICSEARCH_PORT: int = Field(..., ge=1, le=65535)
    ELASTICSEARCH_INDEX: str = Field(default="wood_ai_documents", min_length=1)
    ELASTICSEARCH_TIMEOUT: int = Field(default=30, ge=5, le=300)
    ELASTICSEARCH_MAX_RETRIES: int = Field(default=5, ge=1, le=10)
    ELASTICSEARCH_RETRY_DELAY: int = Field(default=2, ge=1, le=10)

    # AI / ML
    EMBEDDING_MODEL_NAME: str = Field(default="all-MiniLM-L6-v2", min_length=1)
    EMBEDDING_DIMENSION: int = Field(default=384, ge=1)

    # CORS
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000", "http://frontend:3000"])

    # Paths
    DOCUMENTS_PATH: str = Field(default="/app/documents")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    LOG_FORMAT: str = Field(default="json", pattern="^(json|text)$")
    
    # API Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_REQUESTS: int = Field(default=100, ge=1)
    RATE_LIMIT_PERIOD: int = Field(default=60, ge=1)

    @field_validator('ELASTICSEARCH_PORT')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate Elasticsearch port is in valid range"""
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1-65535')
        return v
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @field_validator('DOCUMENTS_PATH')
    @classmethod
    def validate_documents_path(cls, v: str) -> str:
        """Validate documents path exists or can be created"""
        from pathlib import Path
        path = Path(v)
        try:
            path.mkdir(parents=True, exist_ok=True)
            if not path.is_dir():
                raise ValueError(f"Documents path {v} is not a directory")
            # Check write permissions
            test_file = path / ".write_test"
            test_file.touch()
            test_file.unlink()
        except PermissionError:
            raise ValueError(f"No write permission for documents path: {v}")
        except Exception as e:
            raise ValueError(f"Invalid documents path {v}: {e}")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True


settings = Settings()
