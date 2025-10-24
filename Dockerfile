FROM python:3.12-slim

# Install OS-level dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libpq-dev build-essential netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

COPY . .
RUN uv sync

CMD ["sh", "-c", "uv run alembic upgrade head && uv run -m src.api --host ${HOST} --port ${APP_PORT}"]
