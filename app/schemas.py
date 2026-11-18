# app/schemas.py
from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateAdvertRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )

    description: str = Field(
        default="",
        max_length=5000,
    )

    price: float = Field(
        gt=0,
        allow_inf_nan=False,
    )


class CreateAdvertResponse(BaseModel):
    id: int


class GetAdvertQuery(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    author: str | None = Field(default=None, max_length=50)
    price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    created_at: date | None = None


class GetAdvertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    created_at: datetime
    author: str
    price: float


class UpdateAdvertRequest(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    price: float | None = Field(
        default=None,
        gt=0,
        allow_inf_nan=False,
    )


class UpdateAdvertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    author: str
    price: float
    created_at: datetime


class OKResponse(BaseModel):
    status: str = "ok"


class IdResponse(BaseModel):
    id: int


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=72)


class LoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    token: UUID


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=72)


class CreateTodoRequest(BaseModel):
    title: str
    description: str


class GetUserResponse(BaseModel):
    id: int
    name: str


class UpdateUserRequest(BaseModel):
    username: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )
    password: str | None = Field(
        default=None,
        min_length=1,
        max_length=72,
    )
