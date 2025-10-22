FROM python:3.12-slim

# Install OS-level dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    build-essential \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager (fast Python dependency installer)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Copy project files
COPY . .

# Install dependencies (assuming you have pyproject.toml or requirements.txt)
RUN uv sync

# Run Alembic migrations (optional; do this only if you want DB ready at container start)
RUN uv run alembic upgrade head

# Default command to run your app
# Adjust this to your actual entrypoint (e.g., FastAPI, Flask, etc.)
CMD ["uv", "run", "-m", "src.api", "--host", "0.0.0.0", "--port", "8001"]
