# Woods Document Search Engine

AI-powered document search engine PoC for Woods internal documents. Supports keyword search across 3000+ documents with future AI categorization and summarization capabilities.

## Features

- **Keyword Search**: Search documents by matching keywords in titles, headings, and background/scope sections
- **Multiple Format Support**: Parse PDF and DOCX documents
- **Export Functionality**: Export search results to PDF, DOCX, or CSV formats
- **Scalable Architecture**: Built with Elasticsearch for enterprise-level search performance
- **Future AI Ready**: Architecture designed to support AI categorization and summarization

## Tech Stack

- **Backend**: Python 3.11, FastAPI, Elasticsearch 8.11
- **Frontend**: Next.js 14, React 18, Tailwind CSS
- **Infrastructure**: Docker, Docker Compose

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available for Elasticsearch

### Running the Application

1. Clone the repository:
```bash
git clone https://github.com/aaron-seq/woods-document-search-engine.git
cd woods-document-search-engine
```

2. Create a documents folder and add your documents:
```bash
mkdir documents
# Add your PDF and DOCX files to the documents folder
```

3. Start the services:
```bash
docker-compose up -d
```

4. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search` | GET | Search documents by keyword |
| `/ingest` | POST | Ingest documents into the index |
| `/export/{doc_id}` | GET | Export document in specified format |
| `/health` | GET | Health check endpoint |

## Project Structure

```
woods-document-search-engine/
|-- backend/
|   |-- app/
|   |   |-- ingestion/      # Document parsing and indexing
|   |   |-- search/         # Search service
|   |   |-- export/         # Export functionality
|   |   |-- config.py       # Application configuration
|   |   |-- models.py       # Pydantic models
|   |   |-- main.py         # FastAPI application
|   |-- requirements.txt
|   |-- Dockerfile
|-- frontend/
|   |-- pages/              # Next.js pages
|   |-- package.json
|   |-- next.config.js
|   |-- Dockerfile
|-- docker-compose.yml
|-- README.md
```

## Future Enhancements (Phase 2)

- [ ] AI-powered document categorization
- [ ] Automatic summary generation in exports
- [ ] Semantic search capabilities
- [ ] User authentication and access control
- [ ] Advanced analytics dashboard

## License

MIT License - see LICENSE file for details.
