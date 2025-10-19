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
    correlation_id: str = Field(..., description="Request correlation ID for tracking")

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
