import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models import Session, Role, Right

ROLE_RIGHTS = {
    "user": {
        "User": (True, True, True),
        "Advert": (True, True, True),
        "Role": (False, False, True),
        "Right": (False, False, True),
    },
    "admin": {
        "User": (True, True, False),
        "Advert": (True, True, False),
        "Role": (True, True, False),
        "Right": (True, True, False),
    },
}


async def seed_roles():
    async with Session() as session:
        try:
            for role_name, permissions in ROLE_RIGHTS.items():

                result = await session.execute(
                    select(Role)
                    .options(selectinload(Role.rights))
                    .where(Role.name == role_name)
                )
                role = result.scalar_one_or_none()

                if role is None:
                    role = Role(name=role_name, rights=[])
                    session.add(role)
                    await session.flush()

                for model_name, values in permissions.items():
                    read, write, only_own = values

                    result = await session.execute(
                        select(Right).where(
                            Right.model == model_name,
                            Right.read == read,
                            Right.write == write,
                            Right.only_own == only_own,
                        )
                    )

                    right = result.scalar_one_or_none()

                    if right is None:
                        right = Right(
                            model=model_name,
                            read=read,
                            write=write,
                            only_own=only_own,
                        )
                        session.add(right)
                        await session.flush()

                    if right not in role.rights:
                        role.rights.append(right)

                print(f"Роль '{role_name}' успешно настроена.")

            await session.commit()
            print("Первичное заполнение ролей завершено.")

        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_roles())
