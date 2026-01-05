# Woods Document Search Engine - Architecture

This document describes the software architecture of the Woods Document Search Engine, an AI-powered internal document search solution.

## System Context

```mermaid
C4Context
    title System Context Diagram - Woods Document Search Engine
    
    Person(user, "Wood Employee", "Internal user searching documents")
    
    System(searchEngine, "Woods Document Search Engine", "AI-powered document search with semantic understanding")
    
    System_Ext(filesystem, "Document Storage", "PDF/DOCX documents on file system")
    
    Rel(user, searchEngine, "Searches documents", "HTTPS")
    Rel(searchEngine, filesystem, "Reads documents", "File I/O")
```

## Container Diagram

```mermaid
C4Container
    title Container Diagram - Woods Document Search Engine
    
    Person(user, "Wood Employee")
    
    Container(frontend, "Frontend", "Next.js 14", "React-based search UI with Tailwind CSS")
    Container(backend, "Backend API", "FastAPI", "REST API with hybrid search")
    ContainerDb(elasticsearch, "Elasticsearch", "Elasticsearch 8.11", "Full-text and vector search index")
    Container(model, "Embedding Model", "SentenceTransformers", "all-MiniLM-L6-v2 for semantic embeddings")
    
    Rel(user, frontend, "Uses", "HTTPS")
    Rel(frontend, backend, "API calls", "HTTP/JSON")
    Rel(backend, elasticsearch, "Queries/Indexes", "HTTP")
    Rel(backend, model, "Generates embeddings", "In-process")
```

## Component Diagram

```mermaid
flowchart TB
    subgraph Frontend["Frontend (Next.js)"]
        UI[Search UI]
        Preview[Document Preview]
        Export[Export Controls]
    end
    
    subgraph Backend["Backend (FastAPI)"]
        API[API Layer - main.py]
        
        subgraph Services["Services"]
            SearchSvc[SearchService]
            LLMSvc[LLMService]
            IndexerSvc[DocumentIndexer]
            ParserSvc[DocumentParser]
            ExporterSvc[DocumentExporter]
        end
        
        subgraph Utils["Utilities"]
            ESClient[ElasticsearchClientManager]
            Logger[Logging Config]
            Config[Settings]
        end
    end
    
    subgraph Data["Data Layer"]
        ES[(Elasticsearch)]
        Docs[(Document Files)]
    end
    
    UI --> API
    Preview --> API
    Export --> API
    
    API --> SearchSvc
    API --> LLMSvc
    API --> IndexerSvc
    API --> ExporterSvc
    
    SearchSvc --> ESClient
    IndexerSvc --> ParserSvc
    IndexerSvc --> ESClient
    ExporterSvc --> ESClient
    
    ESClient --> ES
    ParserSvc --> Docs
```

## Data Flow

### Search Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant S as SearchService
    participant M as EmbeddingModel
    participant E as Elasticsearch
    
    U->>F: Enter search query
    F->>A: GET /search?query=X
    A->>S: search(query)
    S->>M: encode(query)
    M-->>S: query_vector
    S->>E: Hybrid search (BM25 + KNN)
    E-->>S: Search results
    S-->>A: SearchResponse
    A-->>F: JSON response
    F-->>U: Display results
```

### Document Ingestion Flow

```mermaid
sequenceDiagram
    participant A as API
    participant I as DocumentIndexer
    participant P as DocumentParser
    participant M as EmbeddingModel
    participant E as Elasticsearch
    participant D as Document Files
    
    A->>I: ingest()
    I->>D: List files
    D-->>I: File paths
    
    loop For each document
        I->>P: parse(file_path)
        P->>D: Read file
        D-->>P: File content
        P-->>I: Parsed document
        I->>M: encode(text)
        M-->>I: embedding vector
        I->>E: index(document)
    end
    
    I-->>A: Ingestion results
```

### Summarization Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant S as SearchService
    participant L as LLMService
    participant P as DocumentParser
    participant M as EmbeddingModel
    
    U->>F: Click "Summarize with AI"
    F->>A: POST /summarize
    A->>S: search(query)
    S-->>A: Top 3 results
    A->>P: parse(file_paths)
    P-->>A: Full content
    A->>L: generate_summary(query, docs)
    L->>M: encode(query + sentences)
    M-->>L: embeddings
    L->>L: Find similar sentences
    L-->>A: Extractive summary
    A-->>F: SummaryResponse
    F-->>U: Display summary
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Next.js 14 | Server-side rendering, routing |
| UI | React 18 | Component-based UI |
| Styling | Tailwind CSS | Utility-first CSS |
| Backend | FastAPI | Async REST API |
| Search | Elasticsearch 8.11 | Full-text + vector search |
| ML | SentenceTransformers | Semantic embeddings |
| Parser | pdfplumber, python-docx | Document extraction |
| Export | ReportLab, python-docx | PDF/DOCX generation |
| Container | Docker Compose | Multi-service orchestration |

## Key Design Decisions

### Hybrid Search Architecture

The search combines BM25 keyword matching with semantic vector search:
- **BM25**: Fast, interpretable, great for exact matches
- **KNN Vector Search**: Captures semantic meaning, handles synonyms
- **Combined Score**: Weighted fusion for best of both

### Extractive Summarization

Uses embedding similarity for extractive summarization (not LLM generation):
- No API costs or external dependencies
- Deterministic, reproducible results
- Fast response times
- Privacy-preserving (all processing local)

### Singleton Elasticsearch Client

Connection pooling with retry logic prevents connection exhaustion and handles transient failures gracefully.

## Directory Structure

```
woods-document-search-engine/
├── backend/
│   ├── app/
│   │   ├── ingestion/          # Document parsing, indexing
│   │   ├── search/             # Search, summarization services
│   │   ├── export/             # Export to PDF/DOCX/CSV
│   │   ├── utils/              # Shared utilities
│   │   ├── config.py           # Pydantic settings
│   │   ├── models.py           # Data models
│   │   └── main.py             # FastAPI application
│   ├── tests/                  # Test suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── pages/                  # Next.js pages
│   ├── styles/                 # CSS styles
│   ├── package.json
│   └── Dockerfile
├── documents/                  # Source documents
└── docker-compose.yml
```

## Deployment

### Development

```bash
docker-compose up -d
```

### Production

Use `docker-compose.prod.yml` with:
- Resource limits
- Health checks
- Production environment variables
- No hot-reload
