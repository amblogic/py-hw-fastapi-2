import asyncio
from getpass import getpass

from sqlalchemy import select

from models import Session, User, Role
from auth import hash_password


async def create_user():
    username = input("Введите имя пользователя: ").strip()

    if not username:
        print("Имя пользователя не может быть пустым.")
        return

    password = getpass("Введите пароль: ")
    password_confirm = getpass("Повторите пароль: ")

    if password != password_confirm:
        print("Пароли не совпадают.")
        return

    if len(password.encode("utf-8")) > 72:
        print("Пароль не должен превышать 72 байта.")
        return

    async with Session() as session:
        # Проверяем, существует ли пользователь
        result = await session.execute(select(User).where(User.name == username))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print("Пользователь с таким именем уже существует.")
            return

        # Выбираем роль
        role_name = (
            input("Введите роль (user/admin) [user]: ").strip().lower() or "user"
        )

        if role_name not in ("user", "admin"):
            print("Допустимые роли: user, admin.")
            return

        result = await session.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()

        if role is None:
            print(f"Роль {role_name} не найдена.")
            return

        # Создаём пользователя
        user = User(
            name=username,
            password=hash_password(password),
        )

        user.roles.append(role)

        session.add(user)

        try:
            await session.commit()
            print(f"Пользователь {username} успешно создан!")
            print(f"Назначенная роль: {role_name}")

        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(create_user())
