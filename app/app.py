# app/app.py

from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Query,
    status,
)

from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import models
import schemas

from models import (
    Base,
    engine,
    User,
    Token,
)

from database import get_db_session

from services import (
    add_item,
    get_item,
    update_item,
    delete_item,
    search_adverts,
)

from auth import (
    hash_password,
    check_password,
    check_token,
    require_object_access,
    has_global_object_access,
)

SessionDep = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("Starting up...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    print("Shutting down...")
    await engine.dispose()


app = FastAPI(
    title="My Advertisement App",
    description="Advertisement application API",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {"message": "Hello from FastAPI with DB!"}


@app.post(
    "/login",
    response_model=schemas.LoginResponse,
)
async def login(
    login_data: schemas.LoginRequest,
    session: SessionDep,
):

    query = select(User).where(User.name == login_data.username)

    user = await session.scalar(query)

    if user is None or not check_password(
        login_data.password,
        user.password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    try:
        new_token = Token(user=user)

        session.add(new_token)

        await session.commit()
        await session.refresh(new_token)

        return new_token

    except Exception:
        await session.rollback()
        raise


# Роль всегда назначается автоматически: user.


@app.post(
    "/user",
    response_model=schemas.IdResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    user_data: schemas.CreateUserRequest,
    session: SessionDep,
):

    result = await session.execute(
        select(models.Role).where(models.Role.name == "user")
    )

    user_role = result.scalar_one_or_none()

    if user_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role 'user' not found. Run seed_roles.py first.",
        )

    try:
        new_user = User(
            name=user_data.username,
            password=hash_password(user_data.password),
        )

        new_user.roles.append(user_role)

        session.add(new_user)

        await session.commit()
        await session.refresh(new_user)

        return {"id": new_user.id}

    except ValueError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    except IntegrityError:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    except Exception:
        await session.rollback()
        raise


@app.get(
    "/user/{user_id}",
    response_model=schemas.GetUserResponse,
)
async def get_user(
    user_id: int,
    session: SessionDep,
):

    user = await session.scalar(select(User).where(User.id == user_id))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "id": user.id,
        "name": user.name,
    }


@app.patch(
    "/user/{user_id}",
    response_model=schemas.GetUserResponse,
)
async def update_user(
    user_id: int,
    update_data: schemas.UpdateUserRequest,
    session: SessionDep,
    token_obj: Token = Depends(check_token),
):

    target_user = await session.scalar(select(User).where(User.id == user_id))

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    current_user = token_obj.user

    # Проверяем, изменяет ли пользователь свои данные
    if current_user.id == target_user.id:

        await require_object_access(
            user=current_user,
            orm_object=target_user,
            db_session=session,
            need_write=True,
        )

    else:
        # Чужие данные может менять только администратор
        is_admin = await has_global_object_access(
            user=current_user,
            orm_object=models.User,
            db_session=session,
            need_write=True,
        )

        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can update only your own profile",
            )

    changes = update_data.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data provided for update",
        )

    if "username" in changes:
        target_user.name = changes["username"]

    if "password" in changes:
        target_user.password = hash_password(changes["password"])

    try:
        await session.commit()
        await session.refresh(target_user)

        return {
            "id": target_user.id,
            "name": target_user.name,
        }

    except ValueError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    except IntegrityError:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    except Exception:
        await session.rollback()
        raise


@app.delete(
    "/user/{user_id}",
    response_model=schemas.OKResponse,
)
async def delete_user(
    user_id: int,
    session: SessionDep,
    token_obj: Token = Depends(check_token),
):

    target_user = await session.scalar(select(User).where(User.id == user_id))

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    current_user = token_obj.user

    if current_user.id == target_user.id:

        await require_object_access(
            user=current_user,
            orm_object=target_user,
            db_session=session,
            need_write=True,
        )

    else:
        is_admin = await has_global_object_access(
            user=current_user,
            orm_object=models.User,
            db_session=session,
            need_write=True,
        )

        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can delete only your own account",
            )

    try:
        # Удаляем объявления пользователя
        await session.execute(
            delete(models.Advert).where(models.Advert.user_id == target_user.id)
        )

        # Удаляем связи пользователя с ролями
        target_user.roles.clear()

        # Удаляем пользователя и его токены
        await session.delete(target_user)

        await session.commit()

        return schemas.OKResponse()

    except Exception:
        await session.rollback()
        raise


@app.post(
    "/advertisement",
    response_model=schemas.CreateAdvertResponse,
    summary="Создать новое объявление",
)
async def create_advert(
    advert_data: schemas.CreateAdvertRequest,
    session: SessionDep,
    token_obj: Token = Depends(check_token),
):

    await require_object_access(
        user=token_obj.user,
        orm_object=models.Advert,
        db_session=session,
        need_write=True,
    )

    new_advert = await add_item(
        session=session,
        orm_model=models.Advert,
        item_data=advert_data,
        owner=token_obj.user,
    )

    return schemas.CreateAdvertResponse(id=new_advert.id)


@app.get(
    "/advertisement/{advertisement_id}",
    response_model=schemas.GetAdvertResponse,
    summary="Получить объявление по ID",
)
async def get_advert(
    advertisement_id: int,
    session: SessionDep,
):

    advert = await get_item(
        session=session,
        orm_model=models.Advert,
        item_id=advertisement_id,
    )

    return advert.dict_json


@app.get(
    "/advertisement",
    response_model=list[schemas.GetAdvertResponse],
    summary="Поиск объявлений",
)
async def find_items(
    session: SessionDep,
    title: str | None = Query(
        default=None,
        max_length=200,
    ),
    description: str | None = Query(
        default=None,
        max_length=5000,
    ),
    author: str | None = Query(
        default=None,
        max_length=50,
    ),
    price: float | None = Query(
        default=None,
        gt=0,
    ),
    created_at: date | None = Query(
        default=None,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
):

    query_data = schemas.GetAdvertQuery(
        title=title,
        description=description,
        author=author,
        price=price,
        created_at=created_at,
    )

    return await search_adverts(
        session=session,
        query_data=query_data,
        limit=limit,
        offset=offset,
        user_id=None,
    )


@app.patch(
    "/advertisement/{advertisement_id}",
    response_model=schemas.UpdateAdvertResponse,
    summary="Обновить объявление",
)
async def update_advert(
    advertisement_id: int,
    update_data: schemas.UpdateAdvertRequest,
    session: SessionDep,
    token_obj: Token = Depends(check_token),
):

    advert = await get_item(
        session=session,
        orm_model=models.Advert,
        item_id=advertisement_id,
    )

    await require_object_access(
        user=token_obj.user,
        orm_object=advert,
        db_session=session,
        need_write=True,
    )

    updated_advert = await update_item(
        session=session,
        orm_model=models.Advert,
        item_id=advertisement_id,
        update_data=update_data,
    )

    return schemas.UpdateAdvertResponse(**updated_advert.dict_json)


@app.delete(
    "/advertisement/{advertisement_id}",
    response_model=schemas.OKResponse,
    summary="Удалить объявление",
)
async def delete_advert(
    advertisement_id: int,
    session: SessionDep,
    token_obj: Token = Depends(check_token),
):

    advert = await get_item(
        session=session,
        orm_model=models.Advert,
        item_id=advertisement_id,
    )

    await require_object_access(
        user=token_obj.user,
        orm_object=advert,
        db_session=session,
        need_write=True,
    )

    await delete_item(
        session=session,
        orm_model=models.Advert,
        item_id=advertisement_id,
    )

    return schemas.OKResponse()
