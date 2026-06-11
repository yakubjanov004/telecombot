from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import User, UserRole


class UserRepo:
    @staticmethod
    async def get_user(session: AsyncSession, tg_id: int) -> User | None:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalars().first()

    @staticmethod
    async def create_user(
        session: AsyncSession,
        tg_id: int,
        full_name: str | None = None,
        username: str | None = None,
        phone: str | None = None,
        lang: str = "uz",
        role: UserRole = UserRole.CLIENT,
        is_simulated: bool = False,
    ) -> User:
        user = User(
            tg_id=tg_id,
            full_name=full_name,
            username=username,
            phone=phone,
            lang=lang,
            role=role,
            is_simulated=is_simulated,
        )
        session.add(user)
        await session.commit()
        return user

    @staticmethod
    async def get_or_create(
        session: AsyncSession,
        tg_id: int,
        full_name: str | None = None,
        username: str | None = None,
        lang: str = "uz",
        role: UserRole = UserRole.CLIENT,
    ) -> User:
        user = await UserRepo.get_user(session, tg_id)
        if not user:
            user = await UserRepo.create_user(
                session, 
                tg_id, 
                full_name=full_name, 
                username=username, 
                lang=lang,
                role=role
            )
        return user

    @staticmethod
    async def update_lang(session: AsyncSession, tg_id: int, lang: str):
        await session.execute(
            update(User).where(User.tg_id == tg_id).values(lang=lang)
        )
        await session.commit()

    @staticmethod
    async def update_phone(session: AsyncSession, tg_id: int, phone: str):
        await session.execute(
            update(User).where(User.tg_id == tg_id).values(phone=phone)
        )
        await session.commit()
