from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class TransactionCreate(BaseModel):
    transaction_id: Optional[UUID] = None
    timestamp: Optional[datetime] = None
    sender_account: str
    receiver_account: str
    amount: float
    transaction_type: str
    merchant_category: Optional[str] = None
    location: Optional[str] = None
    device_used: Optional[str] = None
    is_fraud: bool = False
    fraud_type: Optional[str] = None
    time_since_last_transaction: Optional[float] = None
    spending_deviation_score: Optional[float] = None
    velocity_score: Optional[float] = None
    geo_anomaly_score: Optional[float] = None
    payment_channel: Optional[str] = None
    ip_address: Optional[str] = None
    device_hash: Optional[str] = None

    @classmethod
    def model_validate(cls, obj):
        return super().model_validate(obj)


class TransactionQueued(BaseModel):
    transaction_id: UUID
    queued_at: datetime
    correlation_id: UUID