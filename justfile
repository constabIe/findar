#!/usr/bin/env just --justfile

# default recipe to display help information
default:
  @just --list

# Initialize environment variables
env: 
  cp .example.secrets.toml .secrets.toml
  cp docker/.env.example .env
  
# Apply migrations
migrate: env
  uv run alembic upgrade head

# Start application
run: env 
  uv sync
  uv run -m src.api

# docker compose build 
build *args: env
  docker compose build {{args}}

# docker compose up
up *args: env
  docker compose up {{args}} -d

# docker compose restart
restart *args: env
  docker compose restart {{args}}

# docker compose down
down *args:
  docker compose down {{args}}

# docker compose kill
kill *args:
  docker compose kill {{args}}

# docker ps
ps:
  docker ps
  
# Confirm auto lint action  
confirm-lint:
  git add .
  git commit -m "chore: linting"
