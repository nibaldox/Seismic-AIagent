# syntax=docker/dockerfile:1.6
# ============================================================
# STAGE 1: Builder — build-time dependencies only
# ============================================================
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    libxml2-dev \
    libxslt1-dev \
    curl \
    && rm -rf /var/lib/apt/lists*

# Pre-install Python build tools
RUN pip install --upgrade pip wheel

# Install all Python deps (builds C extensions)
COPY requirements.txt .
RUN pip install --compile -r requirements.txt

# ============================================================
# STAGE 2: Runtime — minimal production image
# ============================================================
FROM python:3.13-slim AS runtime

# Create non-root user with fixed UID/GID for consistency
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Runtime-only apt dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 \
    liblapack3 \
    libxml2 \
    libxslt1.1 \
    curl \
    && rm -rf /var/lib/apt/lists*

WORKDIR /app

# Copy compiled Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (after builder so layer cache is better)
COPY --chown=appuser:appgroup . .

# Create app directories with correct ownership
RUN mkdir -p /app/data /app/uploaded_files /app/logs \
    && chown -R appuser:appgroup /app/data /app/uploaded_files /app/logs

# Switch to non-root user
USER appuser

# Environment variables — production defaults
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OLLAMA_HOST=http://localhost:11434 \
    AGNO_LOG_LEVEL=INFO

# Expose Streamlit default port
EXPOSE 8501

# Healthcheck — correct for Streamlit 1.32+
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run as non-root
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]