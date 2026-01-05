# Contributing to Woods Document Search Engine

Thank you for your interest in contributing to the Woods Document Search Engine. This document provides guidelines and instructions for contributing.

## Table of Contents

- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Git Workflow](#git-workflow)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)

---

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Git

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies
```

### Frontend Setup

```bash
cd frontend
npm install
```

### Running Locally

```bash
# Start Elasticsearch
docker-compose up elasticsearch -d

# Backend (in separate terminal)
cd backend
uvicorn app.main:app --reload --port 8000

# Frontend (in separate terminal)
cd frontend
npm run dev
```

---

## Code Style

### Python (Backend)

We follow PEP 8 with these tools:

- **Black**: Code formatter (line length: 88)
- **isort**: Import sorting
- **flake8**: Linting

```bash
# Format code
black app tests
isort app tests

# Check linting
flake8 app tests
```

### JavaScript (Frontend)

- **ESLint**: Linting with Next.js recommended rules
- **Prettier**: Code formatting (optional)

```bash
npm run lint
```

### Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <description>

[optional body]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(search): add semantic search with embeddings
fix(parser): handle corrupted PDF files gracefully
docs(readme): add deployment instructions
test(api): add integration tests for search endpoint
```

---

## Git Workflow

### Branch Naming

```
<type>/<description>
```

Examples:
- `feature/semantic-search`
- `fix/pdf-parsing-error`
- `docs/api-documentation`
- `test/search-service-tests`

### Workflow

1. Create a branch from `main`
2. Make your changes
3. Write/update tests
4. Run linting and tests
5. Commit with descriptive message
6. Push and create Pull Request

```bash
git checkout -b feature/your-feature
# Make changes
git add .
git commit -m "feat(scope): description"
git push origin feature/your-feature
```

---

## Testing Requirements

### Backend Tests

All new code must include tests. Run tests with:

```bash
cd backend
pytest -v --cov=app --cov-report=term-missing
```

Test categories:
- **Unit tests**: Test individual functions/classes with mocks
- **Integration tests**: Test API endpoints (require Elasticsearch)

Mark integration tests appropriately:

```python
import pytest

@pytest.mark.integration
def test_search_with_elasticsearch():
    ...
```

### Coverage Requirements

- Minimum 80% coverage for new code
- Critical paths (search, indexing) require 90%+ coverage

---

## Pull Request Process

### Before Creating PR

1. Run all tests locally
2. Run linting checks
3. Update documentation if needed
4. Rebase on latest `main`

### PR Checklist

- [ ] Tests pass locally
- [ ] Linting passes (black, flake8, eslint)
- [ ] Documentation updated (if applicable)
- [ ] No merge conflicts
- [ ] Descriptive PR title and description
- [ ] Linked to relevant issue (if applicable)

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested the changes

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Linting passes
```

### Review Process

1. Request review from at least one maintainer
2. Address review comments
3. Squash commits if requested
4. Merge after approval

---

## Architecture Guidelines

### Separation of Concerns

Follow the established architecture:

```
backend/app/
├── ingestion/     # Document parsing and indexing (data layer)
├── search/        # Search and LLM services (business logic)
├── export/        # Export functionality (data transformation)
├── utils/         # Shared utilities
├── config.py      # Configuration (environment handling)
├── models.py      # Pydantic models (data contracts)
└── main.py        # FastAPI app (API layer)
```

### Error Handling

- Never use bare `except:` - always specify exception types
- Log all errors with full stack traces
- Return meaningful error messages to clients
- Use structured logging with correlation IDs

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = some_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Operation failed")
```

### Logging

Use structured logging:

```python
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

logger.info("Processing document", extra={"doc_id": doc_id, "file_type": file_type})
```

---

## Questions?

Open an issue for questions or reach out to the maintainers.
