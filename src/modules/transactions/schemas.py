"""
Pydantic schemas for transaction validation and API responses.

This module defines the data validation schemas used for transaction processing,
ensuring data integrity and proper API contract compliance.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    """
    Schema for creating new transactions via API.

    Validates incoming transaction data and ensures all required fields
    are present with appropriate types and constraints.
    """

    amount: float = Field(
        ..., gt=0, description="Transaction amount (must be positive)"
    )
    from_account: str = Field(
        ..., min_length=1, description="Source account identifier"
    )
    to_account: str = Field(
        ..., min_length=1, description="Destination account identifier"
    )
    type: str = Field(..., description="Type of transaction")
    # correlation_id: Optional[str] = Field(default=None, description="Request correlation ID for tracking")

    # Optional fields with defaults
    currency: str = Field(default="USD", description="Transaction currency")
    description: Optional[str] = Field(
        default=None, description="Transaction description"
    )
    merchant_id: Optional[str] = Field(
        default=None, description="Merchant identifier for payments"
    )
    location: Optional[str] = Field(default=None, description="Transaction location")
    device_id: Optional[str] = Field(
        default=None, description="Device used for transaction"
    )
    ip_address: Optional[str] = Field(
        default=None, description="IP address of transaction origin"
    )


class TransactionQueued(BaseModel):
    """
    Schema for transaction queue response.

    Returned after successfully enqueuing a transaction, providing
    the transaction ID, correlation ID, and queue timestamp.
    """

    id: UUID = Field(..., description="Unique transaction identifier")
    queued_at: datetime = Field(
        ..., description="Timestamp when transaction was queued"
    )
    correlation_id: str = Field(..., description="Correlation ID for request tracking")


class TransactionResponse(BaseModel):
    """
    Schema for transaction information response.

    Represents complete transaction data returned from API queries.
    """

    id: UUID = Field(..., description="Unique transaction identifier")
    amount: float = Field(..., description="Transaction amount")
    from_account: str = Field(..., description="Source account identifier")
    to_account: str = Field(..., description="Destination account identifier")
    type: str = Field(..., description="Type of transaction")
    status: str = Field(..., description="Transaction processing status")
    correlation_id: str = Field(..., description="Correlation ID for request tracking")

    # Additional fields
    currency: str = Field(..., description="Transaction currency")
    description: Optional[str] = Field(
        default=None, description="Transaction description"
    )
    merchant_id: Optional[str] = Field(default=None, description="Merchant identifier")
    location: Optional[str] = Field(default=None, description="Transaction location")
    device_id: Optional[str] = Field(default=None, description="Device identifier")
    ip_address: Optional[str] = Field(default=None, description="IP address of origin")

    # Timestamps
    timestamp: datetime = Field(..., description="Transaction timestamp")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")

    # Review fields
    reviewed_at: Optional[datetime] = Field(
        default=None, description="Timestamp when reviewed by analyst"
    )
    review_comment: Optional[str] = Field(
        default=None, description="Analyst's review comment"
    )

    class Config:
        """Pydantic configuration."""

        from_attributes = True  # Enable ORM mode for SQLModel compatibility


class TransactionListResponse(BaseModel):
    """
    Schema for list of transactions response.

    Returns paginated transaction list with metadata.
    """

    transactions: list[TransactionResponse] = Field(
        ..., description="List of transactions"
    )
    count: int = Field(..., description="Number of transactions returned")
    limit: Optional[int] = Field(
        default=None, description="Limit applied to query (if any)"
    )


class TransactionReviewRequest(BaseModel):
    """
    Schema for transaction review request.

    Used when an analyst manually reviews a flagged/failed transaction
    and decides to accept or reject it.
    """

    status: str = Field(
        ...,
        description="New status after review (must be 'accepted' or 'rejected')",
        pattern="^(accepted|rejected)$",
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional comment explaining the review decision",
    )


class TransactionReviewResponse(BaseModel):
    """
    Schema for transaction review response.

    Returns updated transaction information after successful review.
    """

    id: UUID = Field(..., description="Transaction ID")
    status: str = Field(..., description="Updated transaction status")
    reviewed_at: datetime = Field(..., description="Timestamp of the review")
    review_comment: Optional[str] = Field(
        default=None, description="Analyst's review comment"
    )

    class Config:
        """Pydantic configuration."""

        from_attributes = True
