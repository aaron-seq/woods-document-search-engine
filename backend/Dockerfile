FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model during build to avoid cold start
# This reduces first request latency and ensures model availability
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY ./app ./app

# Create documents directory with proper permissions
RUN mkdir -p /app/documents && chmod 755 /app/documents

# Expose application port
EXPOSE 8000

# Health check for container orchestration
# Increased start-period to account for model loading time
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Production command using gunicorn with uvicorn workers
# - 4 workers for better concurrency (adjust based on CPU cores)
# - 120s timeout for long-running operations
# - 30s graceful timeout for clean shutdown
# - Logs to stdout for container log aggregation
CMD ["gunicorn", "app.main:app", \\
     "--bind", "0.0.0.0:8000", \\
     "--workers", "4", \\
     "--worker-class", "uvicorn.workers.UvicornWorker", \\
     "--timeout", "120", \\
     "--graceful-timeout", "30", \\
     "--access-logfile", "-", \\
     "--error-logfile", "-", \\
     "--log-level", "info"]
