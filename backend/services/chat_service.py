import asyncio
import os
import uuid
import logging
import math
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend.repositories.session_repository import SessionRepository
from backend.repositories.message_repository import MessageRepository
from backend.adapters.telegram_adapter import TelegramAdapter
from backend.adapters.websocket_manager import ws_manager
from backend.models import ChatSession, TopicStatusEnum, ServiceType
from backend.config import CHAT_GROUP_ID, INTERNET_TOPIC_ID, MOBILE_TOPIC_ID, CLIENT_RATE_LIMIT_SECONDS, PUBLIC_BASE_URL, UPLOAD_DIR
from datetime import datetime, timedelta
from backend.models import ChatMessage, InternetApplication, MobileApplication
from sqlalchemy import select, desc, text

logger = logging.getLogger(__name__)


class ChatService:
    # Class-level locks for thread safety during asynchronous operations per session
    _session_locks: Dict[str, asyncio.Lock] = {}

    @classmethod
    def get_lock(cls, session_id: str) -> asyncio.Lock:
        if session_id not in cls._session_locks:
            cls._session_locks[session_id] = asyncio.Lock()
        return cls._session_locks[session_id]

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_repo = SessionRepository(db)
        self.message_repo = MessageRepository(db)
        self.telegram = TelegramAdapter()

    @staticmethod
    def _display_value(value: Optional[str], fallback: str = "Kiritilmagan") -> str:
        text = str(value or "").strip()
        return text or fallback

    def _format_chat_request_message(
        self,
        application_type: str,
        application_id: int,
        app: Optional[InternetApplication | MobileApplication],
    ) -> str:
        service_label = "Internet" if application_type == "internet" else "Mobil"
        text = f"🆕 <b>Yangi chat so'rovi ({service_label} #{application_id})</b>\n\n"

        if not app:
            return text + "<b>Ma'lumot:</b> Ariza topilmadi\n\n<i>⏳ Mijoz operator javobini kutmoqda.</i>"

        tariff = self._display_value(
            getattr(app, "rate_plan_first_connection", None)
            or getattr(app, "selected_tariff_code", None)
        )

        if application_type == "internet":
            location = self._display_value(getattr(app, "branches", None))
            text += f"<b>Lokatsiya:</b> {location}\n"
            text += f"<b>Tanlangan tarif:</b> {tariff}\n"
        else:
            location = self._display_value(getattr(app, "branches", None))
            number = self._display_value(getattr(app, "msisdn", None))
            text += f"<b>Hudud:</b> {location}\n"
            text += f"<b>Tanlangan raqam:</b> {number}\n"
            text += f"<b>Tanlangan tarif:</b> {tariff}\n"

        text += "\n<i>⏳ Mijoz operator javobini kutmoqda. Xabar yozishingiz mumkin.</i>"
        return text

    @staticmethod
    def _is_missing_topic_error(error: Optional[str]) -> bool:
        return bool(error and "message thread not found" in error.lower())

    async def _recover_missing_topic(
        self,
        session: ChatSession,
        session_repo: SessionRepository,
    ) -> Optional[int]:
        logger.warning("Telegram topic missing for session %s; recreating topic", session.session_id)
        await session_repo.mark_topic_deleted(session.session_id)
        refreshed = await session_repo.get_by_session_id(session.session_id)
        if not refreshed:
            return None
        return await self.ensure_topic_local(refreshed, session_repo)

    async def get_or_create_session(self, session_id: Optional[str], client_name: str, phone: Optional[str], application_type: str, application_id: int) -> Dict[str, Any]:
        if session_id:
            existing = await self.session_repo.get_by_session_id(session_id)
            if existing and existing.is_active and existing.topic_status == TopicStatusEnum.ACTIVE:
                return {
                    "session_id": existing.session_id,
                    "client_name": existing.client_name,
                    "phone": existing.phone,
                    "application_type": existing.application_type.value if existing.application_type else None,
                    "application_id": existing.application_id,
                    "topic_status": existing.topic_status.value if existing.topic_status else None,
                    "message": "✅ Existing session returned"
                }
        new_id = str(uuid.uuid4())[:8]
        await self.session_repo.create(new_id, client_name, phone, application_type, application_id)
        return {
            "session_id": new_id,
            "client_name": client_name,
            "phone": phone,
            "application_type": application_type,
            "application_id": application_id,
            "message": "✅ Session created successfully"
        }

    async def create_topic(self, session_id: str, client_name: str, application_type: str, application_id: int) -> Optional[int]:
        """Creates a Telegram forum topic and sends initial application details"""
        topic_name = f"{'Internet' if application_type == 'internet' else 'Mobile'} #{application_id}"
        if client_name:
            topic_name += f" - {client_name}"
            
        topic_id = await self.telegram.create_forum_topic(topic_name)
        if topic_id:
            await self.session_repo.update_topic_info(session_id, topic_id, int(CHAT_GROUP_ID))
            
            try:
                if application_type == "internet":
                    res = await self.db.execute(select(InternetApplication).filter(InternetApplication.id == application_id))
                    app = res.scalar_one_or_none()
                else:
                    res = await self.db.execute(select(MobileApplication).filter(MobileApplication.id == application_id))
                    app = res.scalar_one_or_none()
                msg_text = self._format_chat_request_message(application_type, application_id, app)
                
                reply_markup = self.create_end_button(session_id)
                msg_id = await self.telegram.send_message(msg_text, topic_id, reply_markup=reply_markup)
                if msg_id:
                    await self.telegram.pin_chat_message(msg_id)
                    
                    await self.db.execute(
                        text("UPDATE chat_sessions SET last_bot_message_id = :mid WHERE session_id = :sid"),
                        {"mid": msg_id, "sid": session_id}
                    )
                    await self.db.commit()
            except Exception as e:
                logger.error(f"Error sending initial message: {e}")
                
        return topic_id

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        return await self.session_repo.get_by_session_id(session_id)

    async def get_session_by_topic(self, topic_id: int) -> Optional[ChatSession]:
        return await self.session_repo.get_by_topic_id(topic_id)

    async def get_session_with_messages(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = await self.session_repo.get_by_session_id(session_id)
        if not session:
            return None
        messages = await self.message_repo.get_by_session(session_id)
        return {
            "session_id": session.session_id, 
            "client_name": session.client_name, 
            "phone": session.phone, 
            "application_type": session.application_type.value if session.application_type else None, 
            "application_id": session.application_id, 
            "is_active": bool(session.is_active), 
            "telegram_topic_id": session.telegram_topic_id, 
            "telegram_group_id": session.telegram_group_id, 
            "claimed_by_operator_id": session.claimed_by_operator_id, 
            "topic_status": session.topic_status.value if session.topic_status else None, 
            "topic_created_at": session.topic_created_at.isoformat() if getattr(session, "topic_created_at", None) else None,
            "topic_expires_at": session.topic_expires_at.isoformat() if getattr(session, "topic_expires_at", None) else None, 
            "created_at": session.created_at.isoformat() if session.created_at else None, 
            "updated_at": session.updated_at.isoformat() if session.updated_at else None, 
            "messages": [
                {
                    "id": m.id, 
                    "sender": m.sender, 
                    "message": m.message, 
                    "media_url": m.media_url,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                } for m in messages
            ]
        }

    async def list_sessions(self, only_active: bool = True) -> List[Dict[str, Any]]:
        sessions = await (self.session_repo.list_active() if only_active else self.session_repo.list_all())
        return [{"session_id": s.session_id, "client_name": s.client_name, "phone": s.phone, "application_type": s.application_type.value if s.application_type else None, "application_id": s.application_id, "telegram_topic_id": s.telegram_topic_id, "claimed_by_operator_id": s.claimed_by_operator_id, "topic_status": s.topic_status.value if s.topic_status else None, "topic_expires_at": s.topic_expires_at.isoformat() if getattr(s, "topic_expires_at", None) else None, "updated_at": s.updated_at.isoformat() if s.updated_at else None} for s in sessions]

    async def save_client_message(self, session_id: str, message: str):
        msg = await self.message_repo.create(session_id, "client", message)
        await self.session_repo.update_last_message(session_id)
        return msg

    async def save_operator_message(self, session_id: str, message: str, media_url: Optional[str] = None, skip_telegram: bool = False):
        msg = await self.message_repo.create(session_id, "operator", message, media_url=media_url)
        await self.session_repo.update_last_message(session_id)
        if not skip_telegram:
            asyncio.create_task(self._mirror_operator_to_telegram(session_id, message, media_url=media_url))
        return msg

    async def _mirror_operator_to_telegram(self, session_id: str, message: str, media_url: Optional[str] = None):
        try:
            if "👤 <b>Operator</b>:\n" in message or "👤 Operator:\n" in message:
                return

            from backend.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                local_session_repo = SessionRepository(db)
                session = await local_session_repo.get_by_session_id(session_id)
                if session and session.telegram_topic_id:
                    text = f"👤 <b>Operator</b>:\n{message}" if message else "👤 <b>Operator</b> (Rasm)"
                    for attempt in range(3):
                        err = None
                        if media_url:
                            full_url = media_url
                            if not media_url.startswith("http"):
                                base = PUBLIC_BASE_URL.rstrip('/')
                                full_url = f"{base}{media_url}"
                            
                            msg_id, err = await self.telegram.send_photo_with_error(
                                photo_url=full_url,
                                caption=text,
                                message_thread_id=session.telegram_topic_id
                            )
                        else:
                            msg_id, err = await self.telegram.send_message_with_error(text, session.telegram_topic_id)
                        
                        if msg_id:
                            break
                        if self._is_missing_topic_error(err):
                            new_topic_id = await self._recover_missing_topic(session, local_session_repo)
                            if not new_topic_id:
                                return
                            session = await local_session_repo.get_by_session_id(session_id)
                            continue
                        logger.warning(f"Operator mirror attempt {attempt+1} failed")
                        await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Error mirroring operator message to TG: {e}")

    async def send_to_telegram(self, session_id: str, message: str, client_name: str, topic_id: int) -> bool:
        text = f"👤 <b>{client_name or 'Mehmon'}</b>:\n{message}"
        msg_id, err = await self.telegram.send_message_with_error(text, topic_id)
        if not msg_id and self._is_missing_topic_error(err):
            session = await self.session_repo.get_by_session_id(session_id)
            if not session:
                return False
            topic_id = await self._recover_missing_topic(session, self.session_repo) or 0
            if topic_id:
                msg_id, _ = await self.telegram.send_message_with_error(text, topic_id)
        if msg_id:
            await self.session_repo.update_last_message(session_id)
        return msg_id is not None

    async def send_to_client(self, session_id: str, message: str, sender: str = "operator", media_url: Optional[str] = None, from_server: bool = True) -> bool:
        return await ws_manager.send_message(session_id, sender, message, media_url=media_url, from_server=from_server)

    async def get_messages(self, session_id: str):
        return await self.message_repo.get_by_session(session_id)

    async def ensure_topic(self, session: ChatSession) -> Optional[int]:
        if session.topic_status == TopicStatusEnum.ACTIVE and session.telegram_topic_id:
            return session.telegram_topic_id
        app_type_str = "internet" if session.application_type == ServiceType.INTERNET else "mobile"
        return await self.create_topic(session.session_id, session.client_name, app_type_str, session.application_id or 0)

    async def notify_internet_app(
        self,
        app_id: int,
        branches: str,
        departments: str,
        navi_user: str,
        rt_lc_states: str,
        msisdn: str,
        rate_plan_first_connection: str,
        created_at,
    ):
        topic_id = int(INTERNET_TOPIC_ID)
        text = (
            f"📋 <b>Yangi ariza (Internet) #{app_id}</b>\n\n"
            f"<b>Lokatsiya:</b> {self._display_value(branches)}\n"
            f"<b>Tanlangan tarif:</b> {self._display_value(rate_plan_first_connection)}\n"
            f"🕐 <b>Vaqt:</b> {created_at.strftime('%d.%m.%Y %H:%M')}"
        )
        await self.telegram.send_message(text, topic_id)

    async def notify_mobile_app(
        self,
        app_id: int,
        dealer: str,
        navi_user: str,
        msisdn: str,
        rate_plan_first_connection: str,
        branches: str,
        created_at,
    ):
        topic_id = int(MOBILE_TOPIC_ID)
        text = (
            f"📋 <b>Yangi ariza (Mobil) #{app_id}</b>\n\n"
            f"<b>Hudud:</b> {self._display_value(branches)}\n"
            f"<b>Tanlangan raqam:</b> {self._display_value(msisdn)}\n"
            f"<b>Tanlangan tarif:</b> {self._display_value(rate_plan_first_connection)}\n"
            f"🕐 <b>Vaqt:</b> {created_at.strftime('%d.%m.%Y %H:%M')}"
        )
        await self.telegram.send_message(text, topic_id)

    def create_claim_button(self, session_id: str) -> dict:
        return self.create_end_button(session_id)

    def create_operator_keyboard(self) -> dict:
        return {
            "keyboard": [[{"text": "🛑 Chatni tugatish"}]],
            "resize_keyboard": True,
            "one_time_keyboard": False,
        }

    def create_end_button(self, session_id: str) -> dict:
        return {
            "inline_keyboard": [
                [{"text": "🛑 Chatni tugatish", "callback_data": f"end_{session_id}"}]
            ]
        }

    async def is_operator_active(self, session_id: str) -> bool:
        session = await self.session_repo.get_by_session_id(session_id)
        if session and session.claimed_by_operator_id:
            return True
        return False

    async def get_auto_reply(self, message: str) -> Optional[str]:
        if not message:
            return "📎 Rasm yoki fayl qabul qilindi! Operatorimiz tez orada ko'rib chiqadi."
            
        lower_msg = message.lower().strip()
        greetings = (
            "salom",
            "assalom",
            "assalomu alaykum",
            "assalomu aleykum",
            "salam",
            "hello",
            "hi",
        )
        if any(greet in lower_msg for greet in greetings):
            return "👋 Assalom alaykum! Savolingizni yozing, operator tez orada ulanadi."

        templates = [
            (["narx", "narxi", "qancha", "necha", "som", "so'm"], "💳 Narx paketga qarab. Boshlang'ich tariflar 50 000 so'mdan."),
            (["tarif", "paket", "reja"], "📶 Tariflar bo'yicha bir nechta variant bor, operator mosini aytadi."),
            (["qachon", "qachon ulanasiz", "qachon kelasiz", "o'rnatish", "ulanish", "montaj"], "🗓 Ulanish odatda 1-3 ish kuni, operator vaqtni kelishadi."),
            (["hujjat", "pasport", "id", "dokument", "shartnoma"], "🪪 Pasport/ID va manzil kerak bo'ladi, operator ro'yxatini aytadi."),
            (["manzil", "hudud", "qamrov", "xizmat bormi", "mavjudmi"], "📍 Hududga qarab mavjudlik tekshiriladi, manzilingizni yozing."),
            (["tezlik", "mbps", "megabit", "ping"], "⚡ Tezlik tarifga bog'liq, operator aniq variantlarni aytadi."),
            (["router", "modem", "wi-fi", "wifi"], "📡 Router/modem bo'yicha operator yo'naltiradi yoki o'zingizniki bo'lishi mumkin."),
            (["to'lov", "tolov", "oylik", "abonent"], "💳 To'lov shartlari tarifga qarab, operator hisob-kitob qiladi."),
            (["ariza", "status", "holat", "qanday ketayapti"], "📋 Arizangiz holati tekshiriladi, tez orada javob beramiz."),
            (["operator", "konsultant", "odam", "jonli"], "👤 Operator ulanmoqda, iltimos kuting."),
            (["mobil", "sim", "raqam", "nomer"], "📱 Mobil raqam bo'yicha variantlar bor, operator tushuntiradi."),
            (["internet", "provayder"], "🌐 Internet xizmati bo'yicha ma'lumotni operator aniq qiladi."),
        ]
        for keys, reply in templates:
            if any(key in lower_msg for key in keys):
                return reply
        return "✅ Savolingiz uchun rahmat! Operator tez orada javob beradi."

    async def send_welcome_message(self, session_id: str):
        session = await self.session_repo.get_by_session_id(session_id)
        if not session:
            return
            
        messages = await self.message_repo.get_by_session(session_id)
        if len(messages) > 0:
            return

        welcome_text = (
            "✅ Arizangiz yuborildi. Lokatsiya va tarif ma'lumotlari operatorga uzatildi. "
            "Savolingiz bo'lsa, shu chatga yozing."
        )

        await self.message_repo.create(session_id, "system", welcome_text)
        await self.send_to_client(session_id, welcome_text, sender="system")

    async def get_client_retry_after(self, session_id: str) -> int:
        last_msg = await self.message_repo.get_last_by_sender(session_id, "client")
        if not last_msg or not last_msg.created_at:
            return 0
        elapsed = (datetime.utcnow() - last_msg.created_at).total_seconds()
        remaining = CLIENT_RATE_LIMIT_SECONDS - elapsed
        if remaining > 0:
            return int(math.ceil(remaining))
        return 0
        
    async def send_client_message(self, session_id: str, message: str, media_url: Optional[str] = None) -> Dict[str, Any]:
        session = await self.session_repo.get_by_session_id(session_id)
        if not session:
            return {"ok": False, "error": "session_not_found"}
        if not session.is_active or session.topic_status != TopicStatusEnum.ACTIVE:
            return {"ok": False, "error": "session_expired"}

        retry_after = await self.get_client_retry_after(session_id)
        if retry_after > 0:
            return {"ok": False, "error": "rate_limited", "retry_after": retry_after}

        await self.message_repo.create(session_id, "client", message, media_url=media_url)
        await self.session_repo.update_last_message(session_id)

        await self.send_to_client(session_id, message, sender="client", media_url=media_url, from_server=True)

        asyncio.create_task(self._send_to_telegram_background(session_id, message, None, media_url))

        return {"ok": True}

    async def _send_to_telegram_background(self, session_id: str, message: str, auto_reply: Optional[str] = None, media_url: Optional[str] = None):
        lock = self.get_lock(session_id)
        async with lock:
            try:
                from backend.database import AsyncSessionLocal
                async with AsyncSessionLocal() as db:
                    local_session_repo = SessionRepository(db)
                    
                    session = await local_session_repo.get_by_session_id(session_id)
                    if not session or not session.is_active:
                        return

                    topic_id = await self.ensure_topic_local(session, local_session_repo)
                    if not topic_id:
                        return
                    if message or media_url:
                        caption = "<b>Mijoz:</b>"
                        if message:
                            caption += f"\n{message}"
                        elif media_url:
                            caption += "\nRasm yuborildi"

                        for attempt in range(3):
                            err = None
                            if media_url:
                                local_path = None
                                if "/uploads/" in media_url:
                                    filename = media_url.split("/uploads/")[1]
                                    local_path = os.path.join(UPLOAD_DIR, filename)

                                target_photo = local_path if local_path and os.path.exists(local_path) else media_url
                                
                                logger.info(f"Sending photo to TG: {target_photo}")
                                msg_id, err = await self.telegram.send_photo_with_error(
                                    photo_url=target_photo,
                                    caption=caption,
                                    message_thread_id=topic_id
                                )
                            else:
                                msg_id, err = await self.telegram.send_message_with_error(
                                    text=caption,
                                    message_thread_id=topic_id
                                )
                            
                            if msg_id:
                                session.last_bot_message_id = msg_id
                                await db.commit()
                                break
                            if self._is_missing_topic_error(err):
                                new_topic_id = await self._recover_missing_topic(session, local_session_repo)
                                if not new_topic_id:
                                    break
                                topic_id = new_topic_id
                                session = await local_session_repo.get_by_session_id(session_id)
                                continue
                            else:
                                logger.warning(f"TG Send Attempt {attempt+1} failed ({session_id})")
                                await asyncio.sleep(2)

                    if auto_reply:
                        for attempt in range(3):
                            auto_msg_id, auto_err = await self.telegram.send_message_with_error(
                                text=auto_reply,
                                message_thread_id=topic_id
                            )
                            if auto_msg_id:
                                session.last_bot_message_id = auto_msg_id
                                await db.commit()
                                break
                            if self._is_missing_topic_error(auto_err):
                                new_topic_id = await self._recover_missing_topic(session, local_session_repo)
                                if not new_topic_id:
                                    break
                                topic_id = new_topic_id
                                session = await local_session_repo.get_by_session_id(session_id)
                                continue
                            else:
                                logger.warning(f"TG Auto-Reply Attempt {attempt+1} failed ({session_id}): {auto_err}")
                                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Lock processing error: {e}", exc_info=True)

    async def ensure_topic_local(self, session: ChatSession, session_repo: SessionRepository) -> Optional[int]:
        if session.topic_status == TopicStatusEnum.ACTIVE and session.telegram_topic_id:
            return session.telegram_topic_id
        
        topic_name = f"{'Internet' if session.application_type == ServiceType.INTERNET else 'Mobile'} #{session.application_id}"
        if session.client_name:
            topic_name += f" - {session.client_name}"
            
        topic_id = await self.telegram.create_forum_topic(topic_name)
        if topic_id:
            await session_repo.update_topic_info(session.session_id, topic_id, int(CHAT_GROUP_ID))
            msg_text = (
                f"🆕 <b>Qayta tiklangan chat #{session.application_id}</b>\n"
                f"<b>Mijoz ma'lumoti:</b> {self._display_value(session.client_name)}\n\n"
                "<i>⏳ Mijoz operator javobini kutmoqda.</i>"
            )
            reply_markup = self.create_end_button(session.session_id)
            await self.telegram.send_message(msg_text, topic_id, reply_markup=reply_markup)
        return topic_id
