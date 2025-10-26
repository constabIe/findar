from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.ml.schemas import (
    MLActionResponse,
    MLModelCreateRemote,
    MLModelListResponse,
    MLModelResponse,
)
from src.modules.ml.service import MLModelService
from src.storage.dependencies import get_db_session

router = APIRouter(prefix="/ml", tags=["ml"])


async def get_ml_service(db: AsyncSession = Depends(get_db_session)) -> MLModelService:
    return MLModelService(db)


@router.post(
    "/upload", response_model=MLModelResponse, status_code=status.HTTP_201_CREATED
)
async def upload_model(
    file: UploadFile = File(...),
    meta: str | None = None,  # optional JSON string - parsed by client code if needed
    name: str | None = None,
    version: str | None = None,
    threshold_ml: float = 0.5,
    service: MLModelService = Depends(get_ml_service),
) -> MLModelResponse:
    # save file to models directory
    dest_dir = Path("./models")
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{file.filename}"
    dest = dest_dir / filename
    try:
        with dest.open("wb") as fh:
            shutil.copyfileobj(file.file, fh)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    model_meta = {
        "name": name or file.filename,
        "version": version or "1.0",
        "threshold_ml": threshold_ml,
        "features": {},
    }

    created = await service.register_local(dest, model_meta)
    return MLModelResponse(**created.model_dump())


@router.post(
    "/register", response_model=MLModelResponse, status_code=status.HTTP_201_CREATED
)
async def register_remote_model(
    payload: MLModelCreateRemote, service: MLModelService = Depends(get_ml_service)
) -> MLModelResponse:
    created = await service.register_remote(str(payload.endpoint), payload.model_dump())
    return MLModelResponse(**created.model_dump())


@router.get("/models", response_model=MLModelListResponse)
async def list_models(
    limit: int = 100, offset: int = 0, service: MLModelService = Depends(get_ml_service)
) -> MLModelListResponse:
    models = await service.list_models(limit=limit, offset=offset)
    return MLModelListResponse(
        models=[MLModelResponse(**m.model_dump()) for m in models], total=len(models)
    )


@router.get("/models/{model_id}", response_model=MLModelResponse)
async def get_model(
    model_id: UUID, service: MLModelService = Depends(get_ml_service)
) -> MLModelResponse:
    m = await service.get_model(model_id)
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    return MLModelResponse(**m.model_dump())


@router.post("/{model_id}/activate", response_model=MLActionResponse)
async def activate_model(
    model_id: UUID, service: MLModelService = Depends(get_ml_service)
) -> MLActionResponse:
    res = await service.activate(model_id)
    if not res:
        raise HTTPException(status_code=404, detail="Model not found")
    return MLActionResponse(success=True, message="activated")


@router.post("/{model_id}/deactivate", response_model=MLActionResponse)
async def deactivate_model(
    model_id: UUID, service: MLModelService = Depends(get_ml_service)
) -> MLActionResponse:
    res = await service.deactivate(model_id)
    if not res:
        raise HTTPException(status_code=404, detail="Model not found")
    return MLActionResponse(success=True, message="deactivated")


@router.delete("/models/{model_id}", response_model=MLActionResponse)
async def delete_model(
    model_id: UUID, service: MLModelService = Depends(get_ml_service)
) -> MLActionResponse:
    ok = await service.delete(model_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Model not found")
    return MLActionResponse(success=True, message="deleted")


@router.post("/models/{model_id}/test", response_model=MLActionResponse)
async def test_model(
    model_id: UUID,
    payload: Optional[Dict[str, Any]] = None,
    service: MLModelService = Depends(get_ml_service),
) -> MLActionResponse:
    try:
        res = await service.test_model(model_id, payload)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Model not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return MLActionResponse(
        success=res.get("ok", False), message=str(res.get("details"))
    )
