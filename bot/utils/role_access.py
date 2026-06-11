"""Operator / menejer handlerlari uchun rol tekshiruvi."""
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import UserRole
from backend.repositories.user_repository import UserRepo


def tr(lang: str, uz: str, ru: str) -> str:
    return ru if lang == "ru" else uz


async def ensure_roles(
    message: Message,
    session: AsyncSession,
    *allowed: UserRole,
) -> bool:
    user = await UserRepo.get_user(session, message.from_user.id)
    lang = user.lang if user else "uz"
    if user and user.role in allowed:
        return True
    await message.answer(
        tr(
            lang,
            "⛔ Bu bo'lim uchun ruxsat yo'q. .operator yoki .manager orqali kiring.",
            "⛔ Нет доступа. Войдите через .operator или .manager.",
        )
    )
    return False
