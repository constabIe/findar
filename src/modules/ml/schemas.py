from __future__ import annotations

from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class MLModelCreateLocal(BaseModel):
    name: str
    version: str
    threshold_ml: Optional[float] = 0.5
    features: Optional[Dict[str, str]] = Field(default_factory=dict)
    description: Optional[str] = None
    created_by: Optional[UUID] = None


class MLModelCreateRemote(BaseModel):
    name: str
    version: str
    endpoint: HttpUrl
    threshold_ml: Optional[float] = 0.5
    features: Optional[Dict[str, str]] = Field(default_factory=dict)
    description: Optional[str] = None
    created_by: Optional[UUID] = None


class MLModelResponse(BaseModel):
    id: UUID
    name: str
    version: str
    model_type: str
    file_path: Optional[str]
    endpoint: Optional[str]
    threshold_ml: Optional[float]
    features: Optional[Dict[str, str]]
    status: str
    hash: Optional[str]
    size_mb: Optional[float]
    description: Optional[str]
    created_by: Optional[UUID]
    created_at: str


class MLModelListResponse(BaseModel):
    models: List[MLModelResponse]
    total: int


class MLActionResponse(BaseModel):
    success: bool
    message: Optional[str] = None
