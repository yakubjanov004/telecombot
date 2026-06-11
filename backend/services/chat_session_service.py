import random
import logging
import json
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.models import (
    ChatSession,
    SessionEventLog,
    SessionEventType,
    SessionStatus,
    ServiceType,
    ClientMode,
    ClosedReason,
    UserbotState,
    WaitingFor,
    BotTask,
    BotTaskType,
    BotTaskStatus,
    TopicStatusEnum
)
from backend.services.topic_service import TopicService
from bot.core.loader import bot
from backend.services.bot_task_service import BotTaskService

logger = logging.getLogger(__name__)


class ChatSessionService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.topic_service = TopicService(bot)
        self.task_service = BotTaskService(db_session)

    async def start_session(self, client_tg_id: int, service_type: ServiceType, 
                            client_name: str, mode: ClientMode = ClientMode.REAL) -> Optional[ChatSession]:
        try:
            import uuid
            from sqlalchemy import func
            max_id_stmt = select(func.max(ChatSession.id))
            max_id_res = await self.db.execute(max_id_stmt)
            next_id = (max_id_res.scalar() or 0) + 1

            icon = "🌐" if service_type == ServiceType.INTERNET else "📱"
            title = "Internet ulanish" if service_type == ServiceType.INTERNET else "Yangi mobil raqam"
            topic_name = f"{icon} {title} #{next_id}"
            
            thread_id = await self.topic_service.create_topic(topic_name)
            if not thread_id:
                return None
            
            now_utc = datetime.utcnow()
            session = ChatSession(
                session_id=str(uuid.uuid4())[:8],
                client_tg_id=client_tg_id,
                telegram_topic_id=thread_id,
                service_type=service_type,
                client_mode=mode,
                status=SessionStatus.ACTIVE,
                first_message_at=now_utc,
                created_at=now_utc
            )
            self.db.add(session)
            await self.db.flush()
            
            # For Simulated: Client starts, for Real: Operator starts (intro)
            initial_waiting = WaitingFor.CLIENT if mode == ClientMode.SIMULATED else WaitingFor.NONE
            initial_step = "start" if mode == ClientMode.SIMULATED else "greeting"

            initial_collected = {}
            if mode == ClientMode.SIMULATED:
                initial_collected = {
                    "_meta": {"persona": random.choice(["sen", "siz"])}
                }

            state = UserbotState(
                chat_session_id=session.id,
                waiting_for=initial_waiting,
                current_step=initial_step,
                collected_data=json.dumps(initial_collected),
                created_at=now_utc,
            )
            self.db.add(state)
            await self.log_event(session.id, SessionEventType.TOPIC_OPENED, {"name": topic_name})
            
            # Only add SEND_INTRO for REAL clients (bot greets immediately)
            if mode == ClientMode.REAL:
                await self.task_service.add_task(
                    session_id=session.id,
                    task_type=BotTaskType.SEND_INTRO,
                    payload={"text": f"Yangi ariza oydinlashdi.", "pin": True}
                )
            
            await self.db.commit()
            return session
        except Exception as e:
            logger.error(f"Session start error: {e}")
            await self.db.rollback()
            return None

    async def log_event(self, session_id: int, event_type: SessionEventType, data: dict = None, actor_id: int = None):
        log = SessionEventLog(
            chat_session_id=session_id,
            event_type=event_type,
            actor_tg_id=actor_id,
            event_data=json.dumps(data or {}),
            created_at=datetime.utcnow()
        )
        self.db.add(log)
        
    async def update_activity(self, session_id: int, actor: str):
        now = datetime.utcnow()
        fields = {}
        if actor == 'client':
            fields['last_client_message_at'] = now
        elif actor == 'operator':
            fields['last_operator_message_at'] = now
            fields['operator_joined'] = True
        elif actor == 'bot':
            fields['last_bot_message_at'] = now
        stmt = update(ChatSession).where(ChatSession.id == session_id).values(**fields)
        await self.db.execute(stmt)

    async def close_session(self, session_id: int, reason: ClosedReason):
        """Idempotent closure of session and topic."""
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        # Don't close if already closed or cancelled
        if not session or session.status in [SessionStatus.CLOSED, SessionStatus.RESOLVED, SessionStatus.CANCELLED]:
            return
            
        try:
            await self.topic_service.close_topic(session.telegram_topic_id)
        except Exception:
            pass # Topic might be already deleted or closed manually
        
        session.status = SessionStatus.CLOSED
        session.closed_at = datetime.utcnow()
        session.closed_reason = reason
        session.is_active = 0
        session.topic_status = TopicStatusEnum.EXPIRED
        
        await self.log_event(session_id, SessionEventType.TOPIC_CLOSED, {"reason": reason.value})
        
        # Ochiq vazifalarni bekor qilish
        stmt_tasks = update(BotTask).where(
            BotTask.chat_session_id == session_id,
            BotTask.status == BotTaskStatus.PENDING
        ).values(status=BotTaskStatus.FAILED, error_log="Session closed")
        await self.db.execute(stmt_tasks)

        await self.db.commit()
        logger.info(f"Session {session_id} hardened closure finished.")
