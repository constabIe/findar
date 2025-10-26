# Findar

Финансовый радар: Платформа обнаружения подозрительных операций

## Требования

- Python 3.13+
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
cp docker/.env.example .env
```

5. Отредактируйте `.env` с вашими настройками базы данных и Redis.

6. Примените миграции базы данных:

```bash
uv run alembic upgrade head
```

## Запуск

```bash
uv run python -m src.api
```

## Тест нагрузка

```bash
uv run scripts/test.py
```

Чтобы запустить проект с помощью Docker:

1. Инициализируйте переменные окружения:

   cp .env.example .env cd ./src/static/admiral && cp .env.example .env

2. Инициализируйте конфигурации сервисов:

   chmod a+x ./scripts/envsubst.sh ./scripts/envsubst.sh docker

3. Соберите контейнеры:

   docker compose build

4. Запустите проект:

   docker compose up -d

После запуска следующие сервисы будут доступны:

- Админ-панель: [http://localhost](http://localhost)
- Grafana: [http://metrics.localhost](http://metrics.localhost) или
  [http://localhost:4000](http://localhost:4000)
- API: [http://api.localhost](http://api.localhost)
