# ---------- Builder ----------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Optimize build and avoid re-downloading Python
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies only (lock + pyproject)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy full project and install
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---------- Runtime ----------
FROM python:3.12-slim-bookworm AS base

# Create non-root user
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

WORKDIR /app

# Copy environment from builder
COPY --from=builder --chown=nonroot:nonroot /app /app

# Add venv binaries to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Common environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER nonroot

# ----------- API -----------
FROM base AS api
CMD ["python", "-m", "src.api", "--host", "${HOST}", "--port", "${APP_PORT}"]

# ----------- Celery ---------
FROM base AS celery
CMD ["celery", "-A", "src.modules.queue.celery_config:celery_app", "worker", "--loglevel=info", "--queues=transactions,rule_executions,celery", "--pool=solo"]
