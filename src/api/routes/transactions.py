from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from src.modules.transactions.schemas import TransactionCreate, TransactionQueued
from src.modules.transactions.service import enqueue_transaction
from src.storage.dependencies import AsyncRedisDep


router = APIRouter()


@router.post("/transactions", response_model=TransactionQueued)
async def create_transaction(
    payload: TransactionCreate,
    redis_client: Redis = Depends(AsyncRedisDep),
):
    queued = await enqueue_transaction(redis_client=redis_client, data=payload.model_dump())
    from datetime import datetime as _dt

    return TransactionQueued(
        transaction_id=queued["transaction_id"],
        queued_at=_dt.fromisoformat(queued["queued_at"]),
        correlation_id=queued["correlation_id"],
    )


