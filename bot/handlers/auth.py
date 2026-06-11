import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

import backend.config as settings
from backend.models import OperatorType, User, UserRole
from backend.repositories.user_repository import UserRepo
from bot.keyboards.auth import lang_keyboard
from bot.states.auth import AuthState, ManagerAuthState, OperatorAuthState
from bot.utils.role_menu import reply_menu_for_user

router = Router()
logger = logging.getLogger(__name__)


def tr(lang: str, uz: str, ru: str) -> str:
    return ru if lang == "ru" else uz


def staff_login_prompt(lang: str) -> str:
    return tr(
        lang,
        "Bot faqat operator va managerlar uchun.\nKirish uchun .operator yoki .manager yuboring.",
        "Bot tolko dlya operatorov i menedzherov.\nDlya vhoda otpravte .operator ili .manager.",
    )


def _is_ru_choice(text: str) -> bool:
    lowered = text.lower()
    return "russ" in lowered or "\u0440\u0443\u0441" in lowered


def _is_change_language_text(text: str | None) -> bool:
    if not text:
        return False
    return (
        "Tilni o'zgartirish" in text
        or "Izmenit yazyk" in text
        or "\u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c \u044f\u0437\u044b\u043a" in text
    )


@router.message(CommandStart())
async def bot_start(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    user = await UserRepo.get_user(session, message.from_user.id)

    if not user:
        await UserRepo.create_user(
            session,
            message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username,
            lang="uz",
        )
        await message.answer(
            "Iltimos, tilni tanlang:\nPozhaluysta, vyberite yazyk:",
            reply_markup=lang_keyboard(),
        )
        await state.set_state(AuthState.waiting_lang)
        return

    if user.role in (UserRole.OPERATOR, UserRole.MANAGER):
        menu, lang = await reply_menu_for_user(session, message.from_user.id)
        await message.answer(
            tr(lang, "Asosiy menyu", "Glavnoe menyu"),
            reply_markup=menu,
        )
        return

    await message.answer(
        staff_login_prompt(user.lang or "uz"),
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(AuthState.waiting_lang)
async def set_language(message: Message, state: FSMContext, session: AsyncSession):
    text = message.text or ""
    lang_code = "ru" if _is_ru_choice(text) else "uz"
    await UserRepo.update_lang(session, message.from_user.id, lang_code)

    user = await UserRepo.get_user(session, message.from_user.id)
    if user and user.role in (UserRole.OPERATOR, UserRole.MANAGER):
        menu, lang = await reply_menu_for_user(session, message.from_user.id)
        await message.answer(
            tr(lang, "Til tanlandi! Asosiy menyu:", "Yazyk vybran! Glavnoe menyu:"),
            reply_markup=menu,
        )
    else:
        await message.answer(
            staff_login_prompt(lang_code),
            reply_markup=ReplyKeyboardRemove(),
        )
    await state.clear()


@router.message(lambda m: _is_change_language_text(m.text))
async def change_language_request(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    await message.answer(
        "Iltimos, tilni tanlang:\nPozhaluysta, vyberite yazyk:",
        reply_markup=lang_keyboard(),
    )
    await state.set_state(AuthState.waiting_lang)


@router.message(F.text == ".operator")
async def operator_login_cmd(message: Message, state: FSMContext):
    await message.answer("Operator parolini kiriting:")
    await state.set_state(OperatorAuthState.waiting_operator_password)


@router.message(OperatorAuthState.waiting_operator_password)
async def operator_password_verify(message: Message, state: FSMContext, session: AsyncSession):
    password = (message.text or "").strip()
    try:
        await message.delete()
    except Exception:
        pass

    is_operator = password == settings.OPERATOR_PASSWORD
    if not is_operator:
        await message.answer("Xato parol!")
        return

    await message.answer(
        "Iltimos, o'zingizning Navi username'ingizni kiriting "
        "(masalan: OUT_Isayeva, SHPD_Toshmatov):"
    )
    await state.set_state(OperatorAuthState.waiting_navi_username)


@router.message(OperatorAuthState.waiting_navi_username)
async def operator_navi_username(message: Message, state: FSMContext, session: AsyncSession):
    navi = (message.text or "").strip()
    if not navi:
        await message.answer("Iltimos, Navi username kiriting.")
        return

    user = await UserRepo.get_user(session, message.from_user.id)
    lang = user.lang if user else "uz"

    await session.execute(
        update(User)
        .where(User.tg_id == message.from_user.id)
        .values(
            role=UserRole.OPERATOR,
            navi_username=navi,
            operator_type=OperatorType.OUTSOURCE,
        )
    )
    await session.commit()

    menu, _ = await reply_menu_for_user(session, message.from_user.id)
    await message.answer(
        tr(lang, "Muvaffaqiyatli! Endi siz Operatorsiz.", "Uspeshno! Vy voshli kak Operator."),
        reply_markup=menu,
    )
    await state.clear()


@router.message(F.text == ".manager")
async def manager_login_cmd(message: Message, state: FSMContext):
    await message.answer("Manager parolini kiriting:")
    await state.set_state(ManagerAuthState.waiting_manager_password)


@router.message(ManagerAuthState.waiting_manager_password)
async def manager_password_verify(message: Message, state: FSMContext, session: AsyncSession):
    password = (message.text or "").strip()
    try:
        await message.delete()
    except Exception:
        pass

    if password != settings.MANAGER_PASSWORD:
        await message.answer("Xato parol!")
        return

    user = await UserRepo.get_user(session, message.from_user.id)
    lang = user.lang if user else "uz"

    await session.execute(
        update(User).where(User.tg_id == message.from_user.id).values(role=UserRole.MANAGER)
    )
    await session.commit()

    menu, _ = await reply_menu_for_user(session, message.from_user.id)
    await message.answer(
        tr(lang, "Muvaffaqiyatli! Endi siz Managersiz.", "Uspeshno! Teper vy menedzher."),
        reply_markup=menu,
    )
    await state.clear()
