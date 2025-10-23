#!/usr/bin/env just --justfile

# default recipe to display help information
default:
  @just --list

# Initialize environment variables
env:
  cp docker/.env.example .env

# # Apply migrations
# migrate:
#   uv run alembic upgrade head

# # Start application
# run HOST PORT:
#   uv sync
#   just migrate
#   uv run -m src.api --host {{HOST}} --port {{PORT}}

# docker compose build
build *args:
  docker compose build {{args}}

# docker compose up
up *args:
  docker compose up {{args}} -d

# docker compose restart
restart *args:
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

# Delete files ignored by git
clean:
  git clean -Xdf
