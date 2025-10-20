"""
FastAPI router for transaction management endpoints.

This module provides REST API endpoints for transaction operations,
including transaction creation, status checking, and batch operations.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from src.core.logging import get_logger
from src.modules.transactions.schemas import TransactionCreate, TransactionQueued
from src.modules.transactions.service import enqueue_transaction
from src.storage.dependencies import AsyncRedisDep

logger = get_logger("api.transactions")

# Create router instance
router = APIRouter()


@router.post(
    "/transactions",
    response_model=TransactionQueued,
    status_code=status.HTTP_201_CREATED,
    summary="Create Transaction",
    description="Create a new transaction and enqueue it for processing",
)
async def create_transaction(
    payload: TransactionCreate,
    redis_client: AsyncRedisDep,
) -> TransactionQueued:
    """
    Create and enqueue a new transaction for processing.

    This endpoint:
    1. Validates the incoming transaction data using Pydantic schemas
    2. Enqueues the transaction to Redis Stream for asynchronous processing
    3. Triggers Celery workers to process the transaction
    4. Returns transaction metadata including ID and correlation ID

    Args:
        payload: Validated transaction data from request body
        redis_client: Redis client dependency for queue operations

    Returns:
        TransactionQueued: Response containing transaction ID, queue timestamp, and correlation ID

    Raises:
        HTTPException: If transaction validation fails or enqueue operation fails

    Example:
        POST /api/v1/transactions
        {
            "amount": 100.50,
            "from_account": "ACC123",
            "to_account": "ACC456",
            "type": "transfer",
            "correlation_id": "req-123",
            "currency": "USD"
        }
    """
    logger.info(
        "Received transaction creation request",
        event="transaction_create_request",
        amount=payload.amount,
        from_account=payload.from_account,
        to_account=payload.to_account,
    )

    try:
        # Enqueue transaction for processing
        queued = await enqueue_transaction(
            redis_client=redis_client, data=payload.model_dump()
        )

        logger.info(
            "Transaction created successfully",
            event="transaction_create_success",
            transaction_id=queued["id"],
            correlation_id=queued["correlation_id"],
        )

        return TransactionQueued(
            id=queued["id"],
            queued_at=datetime.fromisoformat(queued["queued_at"]),
            correlation_id=queued["correlation_id"],
        )

    except Exception as e:
        logger.error(
            "Transaction creation failed",
            event="transaction_create_error",
            error=str(e),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transaction: {str(e)}",
        )
