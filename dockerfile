# Multi-stage Dockerfile for VisionVend
# Supports both ARM64 (Raspberry Pi) and AMD64 architectures

# ===== BUILDER STAGE =====
FROM python:3.10-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VERSION=1.4.2

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Poetry for dependency management
RUN pip install "poetry==$POETRY_VERSION"

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock* ./

# Configure poetry to not use virtualenvs
RUN poetry config virtualenvs.create false \
    && poetry export -f requirements.txt > requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir uvicorn gunicorn

# ===== FINAL STAGE =====
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/app/.local/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH" \
    TZ=UTC

# Install system dependencies required for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -g 1000 app && \
    useradd -u 1000 -g app -s /bin/bash -m app

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/config /app/secrets \
    && chown -R app:app /app

# Set working directory
WORKDIR /app

# Copy dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=app:app . /app/

# Set proper permissions
RUN chmod -R 755 /app \
    && chmod -R 770 /app/logs /app/data /app/config \
    && chmod -R 600 /app/secrets

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use tini as init system
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run the application with proper worker configuration
CMD ["gunicorn", "VisionVend.server.app:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--log-level", "info", "--access-logfile", "/app/logs/access.log", "--error-logfile", "/app/logs/error.log"]

# Expose port
EXPOSE 8000

# Labels
LABEL org.opencontainers.image.title="VisionVend"
LABEL org.opencontainers.image.description="Smart Vending Machine Hardware and Software"
LABEL org.opencontainers.image.vendor="VisionVend"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="David DeLaurier"
LABEL org.opencontainers.image.source="https://github.com/Artificial-Me/VisionVend"
LABEL org.opencontainers.image.documentation="https://github.com/Artificial-Me/VisionVend/blob/main/README.md"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.created="2025-05-28"
LABEL org.opencontainers.image.base.name="python:3.10-slim"
