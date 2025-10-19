from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, UniqueConstraint


class Transaction(SQLModel, table=True):
    """
    Basic transaction model for rule engine evaluation.

    This model represents financial transactions that will be evaluated
    against fraud detection rules. It will be enhanced later with additional
    fields and relationships.
    """

    __tablename__ = "transactions"  # type: ignore
    __table_args__ = (
        UniqueConstraint("transaction_id", name="uq_transactions_transaction_id"),
        UniqueConstraint("correlation_id", name="uq_transactions_correlation_id"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    amount: float = Field(description="Transaction amount")
    from_account: str = Field(description="Source account identifier")
    to_account: str = Field(description="Destination account identifier")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Transaction timestamp"
    )
    type: TransactionType = Field(description="Type of transaction")
    correlation_id: str = Field(description="Request correlation ID for tracking")
    status: TransactionStatus = Field(
        default=TransactionStatus.QUEUED, description="Transaction processing status"
    )

    # Additional fields for rule evaluation
    currency: str = Field(default="USD", description="Transaction currency")
    description: Optional[str] = Field(
        default=None, description="Transaction description"
    )
    merchant_id: Optional[str] = Field(
        default=None, description="Merchant identifier for payments"
    )
    # merchant_type: Optional[str] = Field(default=None, description="Type/category of merchant")
    location: Optional[str] = Field(default=None, description="Transaction location")
    device_id: Optional[str] = Field(
        default=None, description="Device used for transaction"
    )
    ip_address: Optional[str] = Field(
        default=None, description="IP address of transaction origin"
    )

    # Metadata for rule engine
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record update timestamp"
    )
