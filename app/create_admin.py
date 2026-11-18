
import asyncio

from sqlalchemy import select

from models import Session, User, Role, Right


async def create_admin():
    async with Session() as session:

        # Ищем администратора по имени пользователя
        username = input("Введите username администратора: ")

        result = await session.execute(
            select(User).where(User.name == username)
        )
        user = result.scalar_one_or_none()

        if user is None:
            print("Пользователь не найден. Сначала зарегистрируйте его.")
            return

        # Ищем роль admin
        result = await session.execute(
            select(Role).where(Role.name == "admin")
        )
        admin_role = result.scalar_one_or_none()

        if admin_role is None:
            # Создаем права администратора
            rights = [
                Right(
                    model=model,
                    read=True,
                    write=True,
                    only_own=False
                )
                for model in ["User", "Advert", "Role", "Right"]
            ]

            admin_role = Role(
                name="admin",
                rights=rights
            )

            session.add(admin_role)
            await session.flush()

        # Назначаем роль пользователю, если она еще не назначена
        if admin_role not in user.roles:
            user.roles.append(admin_role)

        await session.commit()

        print(f"Пользователь {username} теперь администратор!")


if __name__ == "__main__":
    asyncio.run(create_admin())