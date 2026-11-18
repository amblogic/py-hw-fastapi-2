# app/models.py

import datetime
import uuid

from typing import Literal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Uuid,
    func,
)

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

from config import config

engine = create_async_engine(
    config.POSTGRES_DSN,
    echo=True,
)

Session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


ModelName = Literal["User", "Advert", "Role", "Right"]


# =========================
# MANY-TO-MANY RELATIONS
# =========================

user_role_relation = Table(
    "user_role_relation",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("advert_user.id"),
        primary_key=True,
    ),
    Column(
        "role_id",
        ForeignKey("role.id"),
        primary_key=True,
    ),
)


role_right_relation = Table(
    "role_right_relation",
    Base.metadata,
    Column(
        "role_id",
        ForeignKey("role.id"),
        primary_key=True,
    ),
    Column(
        "right_id",
        ForeignKey("right.id"),
        primary_key=True,
    ),
)


class Right(Base):
    __tablename__ = "right"

    __table_args__ = (
        CheckConstraint(
            "model IN ('User', 'Advert', 'Role', 'Right')",
            name="check_right_model",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    write: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    only_own: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    model: Mapped[ModelName] = mapped_column(
        String(50),
        nullable=False,
    )


class Role(Base):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    rights: Mapped[list["Right"]] = relationship(
        secondary=role_right_relation,
        lazy="selectin",
    )


# =========================
# USER
# =========================


class User(Base):
    __tablename__ = "advert_user"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    tokens: Mapped[list["Token"]] = relationship(
        "Token",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    roles: Mapped[list["Role"]] = relationship(
        secondary=user_role_relation,
        lazy="selectin",
    )


class Token(Base):
    __tablename__ = "token"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    token: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )

    creation_time: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("advert_user.id"),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="tokens",
        lazy="joined",
    )

    @property
    def to_dict(self):
        return {
            "id": self.id,
            "token": str(self.token),
            "creation_time": self.creation_time.isoformat(),
        }


class Advert(Base):
    __tablename__ = "advertisements"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        String(5000),
        nullable=False,
    )

    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    author: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("advert_user.id"),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship(
        "User",
        lazy="joined",
    )

    @property
    def dict_json(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at,
            "price": self.price,
            "author": self.author,
        }
