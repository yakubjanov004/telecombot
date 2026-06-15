import logging
import os
import uuid
import aiohttp
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

import backend.config as settings
from bot.core.loader import bot
from backend.repositories.session_repository import ChatRepo
from backend.repositories.user_repository import UserRepo
from backend.repositories.event_repository import SessionEventLogRepo
from backend.services.chat_service import ChatService
from backend.models import ClientMode, SessionStatus, SessionEventType, TopicStatusEnum, UserRole

router = Router()
logger = logging.getLogger(__name__)

BACKEND_URL = f"http://localhost:{settings.APP_PORT}"


def tr(lang: str, uz: str, ru: str) -> str:
    return ru if lang == "ru" else uz


async def send_to_backend(session_id: str, message: str, media_url: str = None) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "session_id": session_id,
                "message": message,
                "media_url": media_url,
                "skip_telegram": True
            }
            async with session.post(f"{BACKEND_URL}/api/operator/message", json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                return response.status == 200
    except Exception as e:
        logger.error(f"Error sending to backend: {e}")
        return False


async def _cleanup_closed_topic(
    session: AsyncSession, chat_session, *, notify_client: bool = True
) -> None:
    topic_id = chat_session.telegram_topic_id
    await ChatRepo.close_session(session, chat_session.id, reason="resolved")
    
    await SessionEventLogRepo.log_event(
        session, chat_session.id, SessionEventType.TOPIC_CLOSED
    )

    try:
        from backend.adapters.websocket_manager import ws_manager
        await ws_manager.send_json(
            chat_session.session_id, 
            {"type": "system", "status": "expired", "message": "✅ Chat tugatildi. Yangi ariza bering."}
        )
    except Exception as ws_err:
        logger.warning(f"Failed to notify web client: {ws_err}")

    if notify_client and chat_session.client_tg_id:
        try:
            client_user = await UserRepo.get_user(session, chat_session.client_tg_id)
            lang = client_user.lang if client_user else "uz"
            await bot.send_message(
                chat_id=chat_session.client_tg_id,
                text=tr(lang, "✅ Chat yopildi. Asosiy menyu:", "✅ Чат закрыт. Главное меню:"),
                reply_markup=ReplyKeyboardRemove(),
            )
        except Exception as exc:
            logger.warning("Client notify xatoligi: session=%s err=%s", chat_session.id, exc)

    if topic_id:
        try:
            await bot.delete_forum_topic(chat_id=int(settings.SUPPORT_GROUP_ID), message_thread_id=int(topic_id))
        except Exception as e:
            logger.warning(f"Could not delete forum topic {topic_id}: {e}")


@router.callback_query(F.data == "close_chat")
async def operator_close_chat(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.message or callback.message.chat.id != int(settings.SUPPORT_GROUP_ID):
        return

    topic_id = callback.message.message_thread_id
    chat_session = await ChatRepo.get_session_by_topic(session, topic_id)
    if not chat_session:
        await callback.answer("⚠️ Chat topilmadi!", show_alert=True)
        return

    await _cleanup_closed_topic(session, chat_session)
    await callback.answer("✅ Chat yopildi!")


@router.callback_query(F.data.startswith("claim_"))
async def handle_claim_callback(callback: CallbackQuery, session: AsyncSession):
    try:
        session_id = callback.data.split("_")[1]
        operator_id = callback.from_user.id
        operator_name = callback.from_user.full_name or callback.from_user.username or "Operator"
        
        chat_session = await ChatRepo.get_session_by_topic(session, callback.message.message_thread_id)
        if not chat_session:
            # Fallback using session_id
            from backend.repositories.session_repository import SessionRepository
            repo = SessionRepository(session)
            chat_session = await repo.get_by_session_id(session_id)
            
        if not chat_session:
            await callback.answer("⚠️ Sessiya topilmadi!", show_alert=True)
            return
            
        if chat_session.claimed_by_operator_id:
            await callback.answer("⚠️ Bu chat allaqachon qabul qilingan!", show_alert=True)
            try:
                await bot.edit_message_reply_markup(
                    chat_id=callback.message.chat.id,
                    message_id=callback.message.message_id,
                    reply_markup=None
                )
            except:
                pass
            return
        
        await UserRepo.get_or_create(
            session, 
            operator_id, 
            full_name=callback.from_user.full_name, 
            username=callback.from_user.username,
            role=UserRole.OPERATOR
        )
        
        await ChatRepo.operator_join(session, chat_session.id, operator_id)
        await SessionEventLogRepo.log_event(
            session, chat_session.id, SessionEventType.OPERATOR_JOINED, actor_tg_id=operator_id
        )
        
        # Notify web client if applicable
        if not chat_session.client_tg_id:
            await send_to_backend(session_id, "__operator_claimed__")
        
        await callback.answer(f"✅ Chat {operator_name} tomonidan qabul qilindi!")
        try:
            await bot.edit_message_reply_markup(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="🛑 Chatni tugatish", callback_data=f"end_{session_id}")]]
                ),
            )
        except Exception as e:
            logger.warning(f"Could not update button: {e}")

    except Exception as e:
        logger.error(f"Claim callback error: {e}")
        await callback.answer("❌ Xato yuz berdi!", show_alert=True)


@router.callback_query(F.data.startswith("end_"))
async def handle_end_callback(callback: CallbackQuery, session: AsyncSession):
    try:
        session_id = callback.data.split("_")[1]
        operator_id = callback.from_user.id

        from backend.repositories.session_repository import SessionRepository
        repo = SessionRepository(session)
        chat_session = await repo.get_by_session_id(session_id)
        if not chat_session:
            await callback.answer("⚠️ Sessiya topilmadi!", show_alert=True)
            return

        if chat_session.claimed_by_operator_id and chat_session.claimed_by_operator_id != operator_id:
            await callback.answer("⚠️ Bu chat siz tomonidan qabul qilinmagan!", show_alert=True)
            return

        await _cleanup_closed_topic(session, chat_session)
        await callback.answer("✅ Chat tugatildi!")

    except Exception as e:
        logger.error(f"End callback error: {e}")
        await callback.answer("❌ Xato yuz berdi!", show_alert=True)


@router.message(
    F.chat.id == int(settings.SUPPORT_GROUP_ID),
    F.message_thread_id.is_not(None),
)
async def relay_operator_to_client(message: Message, session: AsyncSession) -> None:
    if not message.from_user:
        return

    # Check the cached userbot ID without starting an interactive Pyrogram login.
    from bot.userbot.client import get_cached_userbot_id
    userbot_id = get_cached_userbot_id()
    is_userbot = bool(userbot_id and message.from_user.id == userbot_id)
    
    if message.from_user.is_bot and not is_userbot:
        return

    topic_id = message.message_thread_id
    chat_session = await ChatRepo.get_session_by_topic(session, topic_id)
    if not chat_session:
        return

    if is_userbot and chat_session.client_mode == ClientMode.REAL:
        return

    if not chat_session.operator_joined and not is_userbot:
        await UserRepo.get_or_create(
            session, 
            message.from_user.id, 
            full_name=message.from_user.full_name, 
            username=message.from_user.username,
            role=UserRole.OPERATOR
        )
        await ChatRepo.operator_join(session, chat_session.id, message.from_user.id)
        await SessionEventLogRepo.log_event(
            session, chat_session.id, SessionEventType.OPERATOR_JOINED, actor_tg_id=message.from_user.id
        )

    # ─── TEXT MESSAGE RELAY ───
    if message.text:
        lower_text = message.text.strip().lower()
        if lower_text in ("🛑 chatni tugatish", "chatni tugatish ✅", "chatni tugatish", "/end"):
            await _cleanup_closed_topic(session, chat_session)
            return

        # If Telegram Client
        if chat_session.client_tg_id:
            try:
                await bot.send_message(chat_session.client_tg_id, message.text)
                await SessionEventLogRepo.log_event(
                    session, 
                    chat_session.id, 
                    SessionEventType.BOT_MESSAGE_SENT,
                    actor_tg_id=message.from_user.id,
                    event_data={"relayed_to_client": True, "actor": "auto-operator" if is_userbot else "operator"}
                )
            except Exception as e:
                logger.error(f"Error sending message to Telegram client: {e}")
        # If Web Client
        else:
            await send_to_backend(chat_session.session_id, message.text)

    # ─── PHOTO MESSAGE RELAY ───
    elif message.photo:
        photo = message.photo[-1]
        caption = message.caption or ""
        
        # If Telegram Client
        if chat_session.client_tg_id:
            try:
                await bot.send_photo(chat_session.client_tg_id, photo.file_id, caption=caption)
            except Exception as e:
                logger.error(f"Error sending photo to Telegram client: {e}")
        # If Web Client
        else:
            try:
                file = await bot.get_file(photo.file_id)
                file_ext = os.path.splitext(file.file_path)[1] if file.file_path else ".jpg"
                file_name = f"{uuid.uuid4().hex}{file_ext}"
                
                # Make sure upload dir exists
                upload_dir = settings.UPLOAD_DIR
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                    
                file_path = os.path.join(upload_dir, file_name)
                await bot.download_file(file.file_path, file_path)
                
                media_url = f"/uploads/{file_name}"
                await send_to_backend(chat_session.session_id, caption, media_url=media_url)
            except Exception as e:
                logger.error(f"Error handling photo for web client: {e}")
