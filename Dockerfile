# =============================================================
# LKIO Production Multi-Stage Dockerfile (API & MCP Engine)
# =============================================================

# Stage 1: Build & Dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build tools for native tree-sitter bindings
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Stage 2: Minimal Runtime Container
FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy compiled virtualenv
COPY --from=builder /app/.venv /app/.venv

# Copy system code
COPY core /app/core
COPY apps /app/apps
COPY config /app/config
COPY benchmarks /app/benchmarks
COPY ingestion /app/ingestion
COPY intelligence /app/intelligence
COPY retrieval /app/retrieval
COPY alembic.ini pyproject.toml uv.lock ./

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check against FastAPI health endpoint
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uv", "run", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
