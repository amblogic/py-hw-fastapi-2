#app/services.py
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import models
import schemas

ADVERT_UPDATE_FIELDS = {
    "title",
    "description",
    "price",
}


async def add_item(
    session: AsyncSession,
    orm_model: type[models.Advert],
    item_data: schemas.CreateAdvertRequest,
    owner: models.User,
) -> models.Advert:
    """
    Создаёт объявление от имени авторизованного пользователя.
    """

    try:
        data = item_data.model_dump()

        # Владелец определяется сервером
        data["user_id"] = owner.id
        data["author"] = owner.name

        new_item = orm_model(**data)

        session.add(new_item)

        await session.commit()
        await session.refresh(new_item)

        return new_item

    except Exception:
        await session.rollback()
        raise


async def get_item(
    session: AsyncSession,
    orm_model: type[models.Advert],
    item_id: int,
) -> models.Advert:
    """
    Получает объект по ID.
    """

    stmt = select(orm_model).where(orm_model.id == item_id)

    result = await session.execute(stmt)

    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"{orm_model.__name__} " f"with id {item_id} not found"),
        )

    return item


async def update_item(
    session: AsyncSession,
    orm_model: type[models.Advert],
    item_id: int,
    update_data: schemas.UpdateAdvertRequest,
) -> models.Advert:
    """
    Обновляет разрешённые поля объявления.
    """

    item = await get_item(
        session,
        orm_model,
        item_id,
    )

    update_dict = update_data.model_dump(
        exclude_unset=True,
    )

    # Удаляем поля, которые не разрешено менять
    update_dict = {
        key: value
        for key, value in update_dict.items()
        if key in ADVERT_UPDATE_FIELDS and value is not None
    }

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields provided for update",
        )

    try:
        for key, value in update_dict.items():
            setattr(item, key, value)

        await session.commit()
        await session.refresh(item)

        return item

    except Exception:
        await session.rollback()
        raise


async def delete_item(
    session: AsyncSession,
    orm_model: type[models.Advert],
    item_id: int,
) -> None:
    """
    Удаляет объект по ID.
    """

    try:
        item = await get_item(
            session,
            orm_model,
            item_id,
        )

        await session.delete(item)

        await session.commit()

    except Exception:
        await session.rollback()
        raise


async def search_adverts(
    session: AsyncSession,
    query_data: schemas.GetAdvertQuery,
    limit: int = 50,
    offset: int = 0,
    user_id: int | None = None,
) -> list[models.Advert]:
    """
    Поиск объявлений с пагинацией.

    user_id:
        None  - поиск по всем объявлениям.
        int   - поиск только по объявлениям пользователя.
    """

    if not 1 <= limit <= 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Limit must be between 1 and 100",
        )

    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Offset cannot be negative",
        )

    stmt = select(models.Advert)

    # Ограничиваем поиск объявлениями пользователя
    if user_id is not None:
        stmt = stmt.where(models.Advert.user_id == user_id)

    filters = query_data.model_dump(
        exclude_none=True,
    )

    if filters.get("title"):
        stmt = stmt.where(models.Advert.title.ilike(f"%{filters['title'].strip()}%"))

    if filters.get("description"):
        stmt = stmt.where(
            models.Advert.description.ilike(f"%{filters['description'].strip()}%")
        )

    if filters.get("author"):
        stmt = stmt.where(models.Advert.author.ilike(f"%{filters['author'].strip()}%"))

    if "price" in filters:
        stmt = stmt.where(models.Advert.price == filters["price"])

    if "created_at" in filters:
        stmt = stmt.where(func.date(models.Advert.created_at) == filters["created_at"])

    stmt = stmt.order_by(models.Advert.created_at.desc()).offset(offset).limit(limit)

    result = await session.execute(stmt)

    return list(result.scalars().all())
