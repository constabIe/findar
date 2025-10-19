from datetime import datetime
from typing import Any, Dict
from uuid import UUID, uuid4

from redis.asyncio import Redis
from celery import Celery
from src.modules.transactions.metrics import transactions_enqueued_total


STREAM_KEY = "transactions:stream"
CELERY_QUEUE = "transactions.consume"


async def enqueue_transaction(redis_client: Redis, data: Dict[str, Any]) -> Dict[str, Any]:
    txn_id = str(data.get("transaction_id") or uuid4())
    correlation_id = str(uuid4())
    now = datetime.utcnow().isoformat()
    payload = {
        "transaction_id": txn_id,
        "queued_at": now,
        "correlation_id": correlation_id,
        **{k: ("" if v is None else str(v)) for k, v in data.items()},
        "status": "queued",
    }
    await redis_client.xadd(STREAM_KEY, fields=payload, maxlen=10000, approximate=True)
    transactions_enqueued_total.inc()
    try:
        from src.workers import celery_app

        celery_app.send_task("transactions.consume")
    except Exception:
        pass
    return {"transaction_id": txn_id, "queued_at": now, "correlation_id": correlation_id}


