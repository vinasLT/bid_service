from typing import TypeVar, Generic, Type, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession = None):
        self.model = model
        self.session = session

    async def get(self, obj_id: int) -> Optional[ModelType]:
        return await self.session.get(self.model, obj_id)

    async def get_all_sorted(self, sort_by: str, sort_order: str = "asc" ) -> Sequence[ModelType]:
        sort_order = sort_order.lower()
        if sort_order not in ("asc", "desc"):
            raise ValueError("sort_order must be either 'asc' or 'desc'")
        sort_field = getattr(self.model, sort_by, None)
        if sort_field is None:
            raise AttributeError(f"Model {self.model.__name__} has no field '{sort_by}'")
        result = await self.session.execute(
            select(self.model).order_by(sort_field.desc() if sort_order == "desc" else sort_field.asc())
        )
        return result.scalars().all()

    async def get_all(self) -> Sequence[ModelType]:
        result = await self.session.execute(select(self.model))
        return result.scalars().all()

    async def get_by_field(self, field_name: str, value):
        field = getattr(self.model, field_name, None)
        if field is None:
            raise AttributeError(f"Model {self.model.__name__} has no field '{field_name}'")
        result = await self.session.execute(
            select(self.model).where(field == value).limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, data: CreateSchemaType, flush: bool = False) -> ModelType:
        obj = self.model(**data.model_dump())
        self.session.add(obj)
        if flush:
            await self.session.flush()
            return obj
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def update(self, obj_id: int, data: UpdateSchemaType) -> Optional[ModelType]:
        obj = await self.get(obj_id)
        if not obj:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, key, value)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj_id: int) -> bool:
        obj = await self.get(obj_id)
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.commit()
        return True
