# Findar

Финансовый радар: Платформа обнаружения подозрительных операций

## Требования

- Python 3.13+
- PostgreSQL 15+
- Redis
- [uv](https://docs.astral.sh/uv/)

## Установка

1. Установите uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Запустите виртуальное окружение. 

3. Установите зависимости:
```bash
uv sync
```

4. Настройте переменные окружения:
```bash
cp config/.env.example .env
```
Отредактируйте `.env` с вашими настройками базы данных и Redis.

5. Создайте `.secrets.toml` в корне проекта. Подробная структура в `.example.secrets.toml`.

6. Примените миграции базы данных:
```bash
uv run alembic upgrade head
```

## Запуск

```bash
uv run python -m src.api
```
