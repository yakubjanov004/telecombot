"""Rol bo'yicha asosiy reply klaviatura."""
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.roles import manager_main_menu, operator_main_menu
from backend.models import UserRole
from backend.repositories.user_repository import UserRepo


ReplyMenu = ReplyKeyboardMarkup | ReplyKeyboardRemove


async def reply_menu_for_user(session: AsyncSession, tg_id: int) -> tuple[ReplyMenu, str]:
    user = await UserRepo.get_user(session, tg_id)
    if not user:
        return ReplyKeyboardRemove(), "uz"

    lang = user.lang or "uz"

    if user.role == UserRole.MANAGER:
        return manager_main_menu(lang), lang

    if user.role == UserRole.OPERATOR:
        op_type = user.operator_type.value if user.operator_type else None
        return operator_main_menu(lang, op_type), lang

    return ReplyKeyboardRemove(), lang


def menu_for_role(role: UserRole | None, lang: str, operator_type: str | None = None) -> ReplyMenu:
    if role == UserRole.MANAGER:
        return manager_main_menu(lang)
    if role == UserRole.OPERATOR:
        return operator_main_menu(lang, operator_type)
    return ReplyKeyboardRemove()
