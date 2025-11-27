from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Application configuration settings"""
    APP_NAME: str = "Wood AI Internal Document Search Engine"
    VERSION: str = "1.0.0"
    
    # Elasticsearch
    ELASTICSEARCH_HOST: str = "elasticsearch"
    ELASTICSEARCH_PORT: int = 9200
    ELASTICSEARCH_INDEX: str = "wood_ai_documents"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://frontend:3000"]
    
    # Paths
    DOCUMENTS_PATH: str = "/app/documents"
    
    class Config:
        env_file = ".env"

settings = Settings()
