# app/auth.py
import bcrypt
import uuid
import datetime

from fastapi import Header, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from models import Token, User, Role, Right, user_role_relation, role_right_relation
from config import TOKEN_TTL
from database import get_db_session


def hash_password(password: str) -> str:
    # Проверяем ограничение bcrypt: максимум 72 байта
    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 72:
        raise ValueError("Password must not exceed 72 bytes")

    # Генерируем соль и хэшируем пароль
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)

    return hashed.decode("utf-8")


def check_password(password: str, hashed_password: str) -> bool:
    # Сравниваем введенный пароль с хэшем
    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 72:
        return False

    try:
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


async def check_token(
    token: uuid.UUID = Header(..., alias="x-token"),
    db_session: AsyncSession = Depends(get_db_session),
) -> Token:
    # Вычисляем дату, раньше которой токен считается просроченным
    expire_threshold = func.now() - datetime.timedelta(seconds=TOKEN_TTL)

    query = select(Token).where(
        Token.token == token,
        Token.creation_time >= expire_threshold,
    )

    token_obj = await db_session.scalar(query)

    if token_obj is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return token_obj


async def check_object_access(
    user: User,
    orm_object,
    db_session: AsyncSession,
    need_read: bool = False,
    need_write: bool = False,
) -> bool:
    """
    Проверяет, есть ли у пользователя права на объект.
    """

    # 1. Определяем имя класса модели
    model_class = orm_object if isinstance(orm_object, type) else orm_object.__class__
    model_name = model_class.__name__

    # 2. Формируем базовые условия для WHERE
    where_args = [User.id == user.id, Right.model == model_name]

    if need_read:
        where_args.append(Right.read.is_(True))

    if need_write:
        where_args.append(Right.write.is_(True))

    # 3. Проверяем принадлежность объекта пользователю
    if not isinstance(orm_object, type) and hasattr(orm_object, "user_id"):
        if orm_object.user_id != user.id:
            # Для чужого объекта нужны права only_own=False
            where_args.append(Right.only_own.is_(False))

    # 4. Формируем запрос на подсчет
    query = (
        select(func.count())
        .select_from(User)
        .join(user_role_relation, User.id == user_role_relation.c.user_id)
        .join(Role, user_role_relation.c.role_id == Role.id)
        .join(role_right_relation, Role.id == role_right_relation.c.role_id)
        .join(Right, role_right_relation.c.right_id == Right.id)
        .where(*where_args)
    )

    # 5. Выполняем запрос
    result = await db_session.execute(query)
    count = result.scalar_one()

    # 6. Если нашли хотя бы одно право — доступ разрешен
    return count > 0


async def require_object_access(
    user: User,
    orm_object,
    db_session: AsyncSession,
    need_read: bool = False,
    need_write: bool = False,
):
    """Проверяет права доступа и возвращает ошибку 403, если доступа нет."""

    has_access = await check_object_access(
        user=user,
        orm_object=orm_object,
        db_session=db_session,
        need_read=need_read,
        need_write=need_write,
    )

    if not has_access:
        raise HTTPException(status_code=403, detail="Permission denied")


async def has_global_object_access(
    user: User,
    orm_object,
    db_session: AsyncSession,
    need_read: bool = False,
    need_write: bool = False,
) -> bool:
    """Проверяет наличие прав на все объекты модели, а не только свои."""

    model_class = orm_object if isinstance(orm_object, type) else orm_object.__class__
    model_name = model_class.__name__

    where_args = [
        User.id == user.id,
        Right.model == model_name,
        Right.only_own.is_(False),
    ]

    if need_read:
        where_args.append(Right.read.is_(True))

    if need_write:
        where_args.append(Right.write.is_(True))

    query = (
        select(func.count())
        .select_from(User)
        .join(user_role_relation, User.id == user_role_relation.c.user_id)
        .join(Role, user_role_relation.c.role_id == Role.id)
        .join(role_right_relation, Role.id == role_right_relation.c.role_id)
        .join(Right, role_right_relation.c.right_id == Right.id)
        .where(*where_args)
    )

    result = await db_session.execute(query)
    return result.scalar_one() > 0
