FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for health check
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformers model during build
# This reduces startup time and ensures model is cached
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application
COPY ./app ./app

# Create documents directory
RUN mkdir -p /app/documents

EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production: Use gunicorn with uvicorn workers
# - 4 workers for better concurrency (adjust based on CPU cores)
# - 120s timeout for long-running requests (embedding generation)
# - 30s graceful shutdown to finish in-flight requests
# - Logs to stdout for container logging
CMD ["gunicorn", "app.main:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
