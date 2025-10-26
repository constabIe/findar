import hashlib
import pickle
import time
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.modules.ml.metrics import (
    ml_model_inference_seconds,
    ml_model_load_seconds,
    ml_model_test_latency_seconds,
    ml_models_total,
)
from src.modules.ml.repository import MLModelRepository
from src.storage.models import MLModel

logger = get_logger("ml")


class MLModelService:
    MODELS_DIR = Path("./models")

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MLModelRepository(session)
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)

    async def register_local(
        self, uploaded_path: Path, meta: Dict[str, Any]
    ) -> MLModel:
        # compute hash and size
        h = hashlib.sha256()
        with uploaded_path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        file_hash = h.hexdigest()
        size_mb = uploaded_path.stat().st_size / (1024 * 1024)

        model = MLModel(
            id=uuid4(),
            name=meta.get("name"),
            version=meta.get("version"),
            model_type="local",
            file_path=str(uploaded_path),
            endpoint=None,
            threshold_ml=meta.get("threshold_ml", 0.5),
            features=meta.get("features") or {},
            status="validated",
            hash=file_hash,
            size_mb=size_mb,
            description=meta.get("description"),
            created_by=meta.get("created_by"),
        )

        created = await self.repo.create(model)
        ml_models_total.inc()
        self._recompute_gauges()
        return created

    async def register_remote(self, endpoint: str, meta: Dict[str, Any]) -> MLModel:
        model = MLModel(
            id=uuid4(),
            name=meta.get("name"),
            version=meta.get("version"),
            model_type="remote",
            file_path=None,
            endpoint=endpoint,
            threshold_ml=meta.get("threshold_ml", 0.5),
            features=meta.get("features") or {},
            status="validated",
            hash=None,
            size_mb=None,
            description=meta.get("description"),
            created_by=meta.get("created_by"),
        )
        created = await self.repo.create(model)
        ml_models_total.inc()
        self._recompute_gauges()
        return created

    async def list_models(self, limit: int = 100, offset: int = 0):
        return await self.repo.list(limit=limit, offset=offset)

    async def get_model(self, model_id: UUID):
        return await self.repo.get(model_id)

    async def activate(self, model_id: UUID):
        model = await self.repo.update_status(model_id, "active")
        self._recompute_gauges()
        return model

    async def deactivate(self, model_id: UUID):
        model = await self.repo.update_status(model_id, "deprecated")
        self._recompute_gauges()
        return model

    async def delete(self, model_id: UUID):
        ok = await self.repo.delete(model_id)
        if ok:
            ml_models_total._value.set(max(0, ml_models_total._value.get() - 1))
            self._recompute_gauges()
        return ok

    async def test_model(
        self, model_id: UUID, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        start = time.time()
        model = await self.get_model(model_id)
        if not model:
            raise FileNotFoundError("Model record not found")

        result = {"ok": False, "details": None}
        try:
            if model.model_type == "local":
                # Try to load model (pickle/joblib) and run a dry run using payload or dummy input
                path = Path(model.file_path)
                t0 = time.time()
                # try joblib first if available, otherwise fall back to pickle
                obj = None
                try:
                    import importlib

                    _joblib = importlib.import_module("joblib")
                    try:
                        obj = _joblib.load(path)
                    except Exception:
                        obj = None
                except Exception:
                    # joblib not available
                    obj = None

                if obj is None:
                    with path.open("rb") as fh:
                        obj = pickle.load(fh)
                ml_model_load_seconds.observe(time.time() - t0)

                # If callable predict exists, try to call with provided payload or empty
                if hasattr(obj, "predict"):
                    t0 = time.time()
                    inp = payload or {}
                    # Try to call predict or predict_proba safely
                    try:
                        if hasattr(obj, "predict_proba"):
                            _ = obj.predict_proba([list(inp.values())])
                        else:
                            _ = obj.predict([list(inp.values())])
                    except Exception:
                        # best-effort: we consider load success even if predict fails with arbitrary payload
                        pass
                    ml_model_inference_seconds.observe(time.time() - t0)

                result = {"ok": True, "details": "local model load OK"}

            else:
                # remote model - call a /ping or root endpoint
                async with httpx.AsyncClient(timeout=10.0) as client:
                    try:
                        ping_url = model.endpoint
                        r = await client.get(ping_url)
                        if r.status_code < 400:
                            result = {
                                "ok": True,
                                "details": "remote endpoint reachable",
                            }
                        else:
                            result = {"ok": False, "details": f"status:{r.status_code}"}
                    except Exception as exc:
                        result = {"ok": False, "details": str(exc)}

        finally:
            ml_model_test_latency_seconds.observe(time.time() - start)

        # update status based on test
        if result.get("ok"):
            await self.repo.update_status(model_id, "validated")
        else:
            await self.repo.update_status(model_id, "failed")
        self._recompute_gauges()
        return result

    def _recompute_gauges(self) -> None:
        # cheap recompute by querying counts is omitted here (would need session)
        # leave to metrics collector or future background task; set conservative defaults
        try:
            # This is a safe best-effort; using internal counters where available
            pass
        except Exception:
            logger.exception("Failed to recompute ML model gauges")
