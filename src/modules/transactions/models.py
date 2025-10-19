from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, UniqueConstraint


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"  # type: ignore
    __table_args__ = (
        UniqueConstraint("transaction_id", name="uq_transactions_transaction_id"),
        UniqueConstraint("correlation_id", name="uq_transactions_correlation_id"),
    )

    transaction_id: UUID = Field(default_factory=uuid4, primary_key=True, unique=True)
    correlation_id: UUID = Field(default_factory=uuid4, unique=True, index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sender_account: str = Field()
    receiver_account: str = Field()
    amount: float = Field()
    transaction_type: str = Field()
    status: str = Field(default="queued", index=True)
    merchant_category: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)
    device_used: Optional[str] = Field(default=None)
    is_fraud: bool = Field(default=False)
    fraud_type: Optional[str] = Field(default=None)
    time_since_last_transaction: Optional[float] = Field(default=None)
    spending_deviation_score: Optional[float] = Field(default=None)
    velocity_score: Optional[float] = Field(default=None)
    geo_anomaly_score: Optional[float] = Field(default=None)
    payment_channel: Optional[str] = Field(default=None)
    ip_address: Optional[str] = Field(default=None)
    device_hash: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


