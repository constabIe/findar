"""
FastAPI router for transaction management endpoints.

This module provides REST API endpoints for transaction operations,
including transaction creation, status checking, and batch operations.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.core.logging import get_logger
from src.modules.transactions.dependencies import AsyncSessionDep
from src.modules.transactions.repository import TransactionRepository
from src.modules.transactions.schemas import (
    TransactionCreate,
    TransactionListResponse,
    TransactionQueued,
    TransactionResponse,
    TransactionReviewRequest,
    TransactionReviewResponse,
)
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
    session: AsyncSessionDep,
    max_composite_depth: int = Query(
        5,
        ge=1,
        le=10,
        description="Maximum recursion depth for composite rule evaluation (1-10)",
    ),
) -> TransactionQueued:
    """
    Create and enqueue a new transaction for processing.

    This endpoint:
    1. Validates the incoming transaction data using Pydantic schemas
    2. Saves transaction to PostgreSQL database
    3. Creates QueueTask record for tracking
    4. Enqueues the transaction to Redis Stream for asynchronous processing
    5. Triggers Celery workers to process the transaction
    6. Returns transaction metadata including ID and correlation ID

    Args:
        payload: Validated transaction data from request body
        redis_client: Redis client dependency for queue operations
        session: Async database session dependency for PostgreSQL operations

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
        # Enqueue transaction for processing (saves to DB, queue, and Redis)
        queued = await enqueue_transaction(
            redis_client=redis_client,
            session=session,
            data=payload.model_dump(),
            max_composite_depth=max_composite_depth,
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


@router.get(
    "/transactions",
    response_model=TransactionListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get All Transactions",
    description="Retrieve all transactions from database with optional limit",
)
async def get_all_transactions(
    session: AsyncSessionDep,
    limit: Optional[int] = Query(
        None,
        ge=1,
        description="Maximum number of transactions to return (default: all)",
    ),
) -> TransactionListResponse:
    """
    Get all transactions from the database.

    This endpoint:
    1. Retrieves transactions from PostgreSQL
    2. Supports optional limit parameter for pagination
    3. Returns transactions ordered by timestamp (newest first)
    4. Returns empty list if no transactions found (not an error)

    Args:
        session: Async database session dependency
        limit: Optional maximum number of transactions to return.
               If not specified, returns all transactions.

    Returns:
        TransactionListResponse: List of transactions with metadata

    Raises:
        HTTPException 500: If database query fails

    Example:
        GET /api/v1/transactions
        GET /api/v1/transactions?limit=10
    """
    logger.info(
        "Retrieving transactions",
        event="get_transactions_request",
        limit=limit,
    )

    try:
        # Create repository instance
        repo = TransactionRepository(session)

        # Get transactions from database
        transactions = await repo.get_all_transactions(limit=limit)

        # Convert to response models
        transaction_responses = [
            TransactionResponse.model_validate(t) for t in transactions
        ]

        logger.info(
            "Transactions retrieved successfully",
            event="get_transactions_success",
            count=len(transactions),
            limit=limit,
        )

        return TransactionListResponse(
            transactions=transaction_responses,
            count=len(transaction_responses),
            limit=limit,
        )

    except Exception as e:
        logger.error(
            "Failed to retrieve transactions",
            event="get_transactions_error",
            error=str(e),
            limit=limit,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve transactions: {str(e)}",
        )
        
        
        


@router.post(
    "/transactions/{transaction_id}/review",
    response_model=TransactionReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Review Transaction",
    description="Manually review a flagged or failed transaction and mark it as accepted or rejected",
)
async def review_transaction_endpoint(
    transaction_id: str,
    payload: TransactionReviewRequest,
    session: AsyncSessionDep,
) -> TransactionReviewResponse:
    """
    Review a flagged or failed transaction.

    This endpoint allows analysts to manually review transactions that were
    flagged or failed by the fraud detection system and make a decision to
    accept or reject them.

    **Business Rules:**
    - Only transactions with status `flagged` or `failed` can be reviewed
    - Review status must be either `accepted` or `rejected`
    - Optional comment can be added to explain the decision
    - Updates `reviewed_at` timestamp and stores the comment

    Args:
        transaction_id: UUID of the transaction to review
        payload: Review request containing status and optional comment
        session: Database session dependency

    Returns:
        TransactionReviewResponse: Updated transaction with review details

    Raises:
        HTTPException 400: Invalid transaction ID, invalid status, or transaction cannot be reviewed
        HTTPException 404: Transaction not found
        HTTPException 500: Internal server error

    Example:
        POST /api/v1/transactions/550e8400-e29b-41d4-a716-446655440000/review
        {
            "status": "accepted",
            "comment": "Verified with customer, legitimate transaction"
        }
    """
    from src.modules.transactions.service import review_transaction

    logger.info(
        "Received transaction review request",
        event="review_request",
        transaction_id=transaction_id,
        status=payload.status,
        has_comment=payload.comment is not None,
    )

    try:
        # Call service function to perform review
        result = await review_transaction(
            session=session,
            transaction_id=transaction_id,
            new_status=payload.status,
            comment=payload.comment,
        )

        logger.info(
            "Transaction review endpoint completed",
            event="review_endpoint_success",
            transaction_id=transaction_id,
        )

        return TransactionReviewResponse(**result)

    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise

    except Exception as e:
        logger.error(
            "Transaction review endpoint failed",
            event="review_endpoint_error",
            transaction_id=transaction_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review transaction: {str(e)}",
        )
