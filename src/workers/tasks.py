from datetime import datetime
from typing import Any, Dict

from celery import shared_task
from redis import Redis as SyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.transactions.models import Transaction
from src.modules.transactions.service import STREAM_KEY
from src.storage.redis import get_sync_redis
from src.storage.sql.engine import get_async_session_maker
from src.modules.transactions.metrics import (
    transactions_processed_total,
    transactions_failed_total,
)


@shared_task(name="transactions.consume")
def consume_transactions() -> int:
    redis: SyncRedis = get_sync_redis()
    session_maker = get_async_session_maker()

    try:
        redis.xgroup_create(name=STREAM_KEY, groupname="transactions", id="0-0", mkstream=True)
    except Exception as e:
        msg = str(e)
        if "BUSYGROUP" not in msg:
            raise

    processed = 0
    consumer = f"worker"

    while True:
        messages = redis.xreadgroup(
            groupname="transactions",
            consumername=consumer,
            streams={STREAM_KEY: ">"},
            count=100,
            block=3000,
        )
        if not messages:
            break

        for _, entries in messages:
            for entry_id, fields in entries:
                processed += 1

                async def write_txn(payload: Dict[str, Any]):
                    async with session_maker() as session:  # type: AsyncSession
                        txn = Transaction(
                            transaction_id=payload.get("transaction_id"),
                            correlation_id=payload.get("correlation_id"),
                            timestamp=datetime.fromisoformat(payload.get("timestamp")) if payload.get("timestamp") else datetime.utcnow(),
                            sender_account=payload.get("sender_account", ""),
                            receiver_account=payload.get("receiver_account", ""),
                            amount=float(payload.get("amount", 0)),
                            transaction_type=payload.get("transaction_type", ""),
                            merchant_category=(payload.get("merchant_category") or None),
                            location=(payload.get("location") or None),
                            device_used=(payload.get("device_used") or None),
                            is_fraud=bool(payload.get("is_fraud", False)),
                            fraud_type=(payload.get("fraud_type") or None),
                            time_since_last_transaction=float(payload.get("time_since_last_transaction")) if payload.get("time_since_last_transaction") not in (None, "") else None,
                            spending_deviation_score=float(payload.get("spending_deviation_score")) if payload.get("spending_deviation_score") not in (None, "") else None,
                            velocity_score=float(payload.get("velocity_score")) if payload.get("velocity_score") not in (None, "") else None,
                            geo_anomaly_score=float(payload.get("geo_anomaly_score")) if payload.get("geo_anomaly_score") not in (None, "") else None,
                            payment_channel=(payload.get("payment_channel") or None),
                            ip_address=(payload.get("ip_address") or None),
                            device_hash=(payload.get("device_hash") or None),
                            status="processed",
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        session.add(txn)
                        await session.commit()

                import asyncio

                try:
                    asyncio.get_event_loop().run_until_complete(write_txn(fields))
                    redis.xack(STREAM_KEY, "transactions", entry_id)
                    transactions_processed_total.inc()
                except Exception:
                    # set failed status marker for visibility
                    transactions_failed_total.inc()
                    redis.xadd(
                        STREAM_KEY,
                        {
                            "transaction_id": fields.get("transaction_id", ""),
                            "correlation_id": fields.get("correlation_id", ""),
                            "status": "failed",
                        },
                        maxlen=10000,
                        approximate=True,
                    )

    return processed


