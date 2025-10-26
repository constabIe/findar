from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.models import MLModel


class MLModelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, model: MLModel) -> MLModel:
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return model

    async def get(self, model_id: UUID) -> Optional[MLModel]:
        res = await self.session.execute(select(MLModel).where(MLModel.id == model_id))
        return res.scalar_one_or_none()

    async def list(self, limit: int = 100, offset: int = 0) -> List[MLModel]:
        res = await self.session.execute(select(MLModel).limit(limit).offset(offset))
        return res.scalars().all()

    async def delete(self, model_id: UUID) -> bool:
        model = await self.get(model_id)
        if not model:
            return False
        await self.session.delete(model)
        await self.session.commit()
        return True

    async def update_status(self, model_id: UUID, status: str) -> Optional[MLModel]:
        model = await self.get(model_id)
        if not model:
            return None
        model.status = status
        await self.session.commit()
        await self.session.refresh(model)
        return model
