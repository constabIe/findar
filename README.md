# Findar


## Технологический стек

### Backend
- **Python 3.13+** — основной язык разработки
- **FastAPI** — асинхронный веб-фреймворк для REST API
- **SQLAlchemy + Alembic** — ORM и миграции базы данных
- **PostgreSQL 16** — основная СУБД
- **Redis** — кэширование и очереди задач
- **Celery** — асинхронная обработка транзакций

### Фронтенд
- **Admiral UI** — веб-интерфейс для мониторинга и управления

### ML модель
Система использует обученную модель машинного обучения для предсказания мошеннических транзакций:
- **Метрика F1-score: 0.87** — достигнутая точность на тестовых данных
- Возможность добавлять свои модели

### Мониторинг и логирование
- **Grafana** — визуализация метрик и дашборды
- **Prometheus** — сбор метрик в реальном времени
- **Loki + Promtail** — централизованное логирование
- **Loguru** — структурированное логирование

### Инфраструктура
- **Docker + Docker Compose** — контейнеризация сервисов
- **Nginx** — reverse proxy и балансировка нагрузки

## Архитектура решения

### Основные модули
- **API** (`src/api`) — REST API для взаимодействия с системой
- **Bot** (`src/bot`) — Telegram бот для уведомлений и управления
- **Rule Engine** (`src/modules/rule_engine`) — движок правил обнаружения мошенничества:
  - Threshold правила (пороговые значения)
  - Pattern правила (анализ паттернов поведения)
  - Composite правила (логические комбинации AND/OR/NOT)
  - ML правила (машинное обучение)
- **Queue** (`src/modules/queue`) — асинхронная обработка транзакций через Celery
- **Notifications** (`src/modules/notifications`) — система уведомлений (Telegram, Email)
- **ML** (`src/modules/ml`) — управление ML моделями и инференс
- **Reporting** (`src/modules/reporting`) — отчеты и аналитика
- **Transactions** (`src/modules/transactions`) — управление транзакциями

### Особенности обработки
1. Транзакции обрабатываются асинхронно через Celery workers
2. Rule engine оценивает каждую транзакцию по всем активным правилам
3. Результаты кэшируются в Redis для быстрого доступа
4. Prometheus метрики собираются на каждом этапе обработки

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
   Не забудьте добавить токен для бота

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
