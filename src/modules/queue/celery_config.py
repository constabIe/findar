"""
Celery configuration for the queue processing module.

Configures Celery with Redis broker, PostgreSQL result backend,
retry policies, and worker settings for distributed task processing.
"""

from celery import Celery
from kombu import Exchange, Queue

from src.storage.redis.client import get_redis_url
from src.storage.sql.engine import get_database_url

# Initialize Celery app
celery_app = Celery("findar_queue")

# Get connection URLs from storage modules
BROKER_URL = get_redis_url()

# Convert async PostgreSQL URL to sync for Celery result backend
RESULT_BACKEND = get_database_url().replace(
    "postgresql+asyncpg://", "db+postgresql://"
)

# Celery Configuration
celery_app.conf.update(
    # Broker settings
    broker_url=BROKER_URL,
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,

    # Result backend
    result_backend=RESULT_BACKEND,
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },
    result_extended=True,  # Store more task metadata
    result_expires=86400,  # Results expire after 24 hours

    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,  # Acknowledge task after completion (important for reliability)
    task_reject_on_worker_lost=True,  # Reject task if worker dies
    task_track_started=True,  # Track when task starts
    task_time_limit=300,  # Hard time limit: 5 minutes
    task_soft_time_limit=240,  # Soft time limit: 4 minutes

    # Worker settings
    worker_prefetch_multiplier=2,  # How many tasks to prefetch per worker process
    worker_max_tasks_per_child=1000,  # Restart worker after N tasks (prevents memory leaks)
    worker_disable_rate_limits=False,
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format=(
        "[%(asctime)s: %(levelname)s/%(processName)s] "
        "[%(task_name)s(%(task_id)s)] %(message)s"
    ),

    # Retry settings (default for all tasks)
    task_autoretry_for=(Exception,),  # Auto-retry on any exception
    task_max_retries=3,  # Maximum retry attempts
    task_default_retry_delay=60,  # Wait 60 seconds between retries

    # Task routing and priority
    task_routes={
        "src.modules.queue.tasks.process_transaction": {
            "queue": "transactions",
            "routing_key": "transaction.process",
        },
        "src.modules.queue.tasks.send_notification": {
            "queue": "notifications",
            "routing_key": "notification.send",
        },
    },

    task_queue_max_priority=20,  # Maximum priority level
    task_default_priority=5,  # Default priority

    # Task queues with priorities
    task_queues=(
        Queue(
            "transactions",
            Exchange("transactions"),
            routing_key="transaction.#",
            queue_arguments={"x-max-priority": 20},
        ),
        Queue(
            "notifications",
            Exchange("notifications"),
            routing_key="notification.#",
            queue_arguments={"x-max-priority": 10},
        ),
        Queue(
            "celery",  # Default queue
            Exchange("celery"),
            routing_key="celery",
        ),
    ),

    # Monitoring and events
    worker_send_task_events=True,  # Send task events for monitoring
    task_send_sent_event=True,  # Send event when task is sent

    # Performance optimizations
    broker_pool_limit=10,  # Connection pool size
    broker_heartbeat=30,  # Heartbeat interval
    broker_transport_options={
        "visibility_timeout": 3600,  # 1 hour
        "fanout_prefix": True,
        "fanout_patterns": True,
    },

    # Beat scheduler (for periodic tasks)
    beat_schedule={
        # Example: Clean up old completed tasks every day
        "cleanup-old-tasks": {
            "task": "src.modules.queue.tasks.cleanup_old_tasks",
            "schedule": 86400.0,  # Run every 24 hours
        },
    },
)

# Auto-discover tasks from modules
celery_app.autodiscover_tasks(
    ["src.modules.queue"],
    force=True
)
