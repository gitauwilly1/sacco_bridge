# ============================================================
# Sacco Bridge - Production Dockerfile
# Multi-stage build for optimized image size
# ============================================================

# ---- Stage 1: Build dependencies ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# ---- Stage 2: Runtime ----
FROM python:3.12-slim

# Create non-root user
RUN groupadd -r sacco && useradd -r -g sacco sacco

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install Python packages from wheels
RUN pip install --no-cache /wheels/* \
    && rm -rf /wheels

# Copy application code (this creates files owned by sacco)
COPY --chown=sacco:sacco . .

# Create necessary directories with correct ownership AFTER copy
RUN mkdir -p /app/logs /app/media /app/staticfiles \
    && chown sacco:sacco /app/logs /app/media /app/staticfiles

# Switch to non-root user
USER sacco

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/schema/ || exit 1

# Default command (overridden in docker-compose for different services)
CMD ["gunicorn", "sacco_bridge.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]