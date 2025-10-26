# ------------- Builder -------------
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

# ------------- Runtime --------------
FROM python:3.12-slim-bookworm AS base

COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Create non-root user
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

WORKDIR /app

# Copy environment from builder
COPY --from=builder --chown=nonroot:nonroot /app /app

# Make folders accessible by dependent services
RUN mkdir -p /app/logs && chown -R nonroot:nonroot /app/logs
RUN mkdir -p /app/models && chown -R nonroot:nonroot /app/models

# Add venv binaries to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Common environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER nonroot

# ------------ MIGRATIONS ------------
FROM base AS migrations
CMD ["uv", "run", "alembic", "upgrade", "head"]

# --------------- API ----------------
FROM base AS api
CMD ["uv", "run", "-m", "src.api"]

# -------------- CELERY --------------
FROM base AS celery
CMD ["uv", "run", "celery", "-A", "src.modules.queue.celery_config:celery_app", "worker", "--loglevel=info", "--queues=transactions,rule_executions,celery", "--pool=solo"]

# -------------- TG BOT --------------
FROM base AS bot
CMD ["uv", "run", "-m", "src.bot"]
