default:
  just --list

migrate:
  uv run alembic upgrade head
  
run:
  uv sync
  uv run -m src.api

env: 
  cp docker/.env.example .env

build *args:
  docker compose build {{args}}

up *args:
  docker compose up {{args}} -d

restart *args:
  docker compose restart {{args}}
  
down *args:
  docker compose down {{args}}

kill *args:
  docker compose kill {{args}}

ps:
  docker ps