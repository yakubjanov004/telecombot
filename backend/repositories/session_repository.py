from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta
from typing import Optional, List
import json
from backend.models import ChatSession, ServiceType, TopicStatusEnum, SessionStatus, BotTask, BotTaskStatus


class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_session_id(self, session_id: str) -> Optional[ChatSession]:
        result = await self.db.execute(select(ChatSession).where(ChatSession.session_id == session_id))
        return result.scalar_one_or_none()

    async def get_by_topic_id(self, topic_id: int) -> Optional[ChatSession]:
        result = await self.db.execute(select(ChatSession).where(ChatSession.telegram_topic_id == topic_id))
        return result.scalar_one_or_none()

    async def create(self, session_id: str, client_name: str, phone: Optional[str], application_type: str, application_id: int) -> ChatSession:
        app_type = ServiceType.INTERNET if application_type == "internet" else ServiceType.MOBILE
        session = ChatSession(
            session_id=session_id,
            client_name=client_name,
            phone=phone,
            application_type=app_type,
            application_id=application_id,
            is_active=1,
            status=SessionStatus.ACTIVE,
            topic_status=TopicStatusEnum.ACTIVE,
            service_type=app_type,
            created_at=datetime.utcnow()
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def update_topic_info(self, session_id: str, topic_id: int, group_id: int) -> None:
        session = await self.get_by_session_id(session_id)
        if session:
            now = datetime.utcnow()
            session.telegram_topic_id = topic_id
            session.telegram_group_id = group_id
            session.topic_status = TopicStatusEnum.ACTIVE
            session.topic_created_at = now
            session.topic_expires_at = now + timedelta(days=7)
            await self.db.commit()

    async def update_last_message(self, session_id: str) -> None:
        session = await self.get_by_session_id(session_id)
        if session:
            session.last_message_at = datetime.utcnow()
            session.updated_at = datetime.utcnow()
            await self.db.commit()

    async def mark_topic_deleted(self, session_id: str) -> None:
        session = await self.get_by_session_id(session_id)
        if session:
            session.topic_status = TopicStatusEnum.DELETED
            session.telegram_topic_id = None
            await self.db.commit()

    async def mark_expired(self, session_id: str) -> None:
        session = await self.get_by_session_id(session_id)
        if session:
            session.is_active = 0
            session.topic_status = TopicStatusEnum.EXPIRED
            session.telegram_topic_id = None
            session.status = SessionStatus.CLOSED
            session.closed_at = datetime.utcnow()
            await self.db.commit()

    async def list_active(self) -> List[ChatSession]:
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.is_active == 1)
            .order_by(ChatSession.updated_at.desc())
        )
        return result.scalars().all()

    async def list_all(self) -> List[ChatSession]:
        result = await self.db.execute(select(ChatSession).order_by(ChatSession.updated_at.desc()))
        return result.scalars().all()


class ChatRepo:
    @staticmethod
    async def get_active_session(session: AsyncSession, client_tg_id: int) -> Optional[ChatSession]:
        result = await session.execute(
            select(ChatSession).where(
                ChatSession.client_tg_id == client_tg_id,
                ChatSession.status == SessionStatus.ACTIVE,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_session_by_topic(session: AsyncSession, topic_id: int) -> Optional[ChatSession]:
        result = await session.execute(
            select(ChatSession).where(
                ChatSession.telegram_topic_id == topic_id,
                ChatSession.status == SessionStatus.ACTIVE,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def create_session(
        session: AsyncSession,
        client_tg_id: int,
        topic_id: int,
        service_type: str,
        initiator_type=None,
        client_mode=None,
    ) -> ChatSession:
        from backend.models import InitiatorType as IT, ClientMode as CM
        # Close previous sessions
        await session.execute(
            update(ChatSession)
            .where(
                ChatSession.client_tg_id == client_tg_id,
                ChatSession.status == SessionStatus.ACTIVE,
            )
            .values(status=SessionStatus.CLOSED, closed_at=datetime.utcnow())
        )
        
        import uuid
        s_id = str(uuid.uuid4())[:8]
        new_session = ChatSession(
            session_id=s_id,
            client_tg_id=client_tg_id,
            telegram_topic_id=topic_id,
            status=SessionStatus.ACTIVE,
            service_type=ServiceType.INTERNET if service_type == "internet" else ServiceType.MOBILE,
            initiator_type=initiator_type or IT.CLIENT,
            client_mode=client_mode or CM.REAL,
            userbot_active=True,
            operator_joined=False,
            created_at=datetime.utcnow()
        )
        session.add(new_session)
        await session.commit()
        await session.refresh(new_session)
        return new_session

    @staticmethod
    async def close_session(session: AsyncSession, session_id: int, reason=None):
        from backend.models import ClosedReason
        r = ClosedReason.RESOLVED
        if reason == "timeout":
            r = ClosedReason.TIMEOUT
        elif reason == "cancelled":
            r = ClosedReason.CANCELLED
        elif reason == "error":
            r = ClosedReason.ERROR
            
        await session.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(
                status=SessionStatus.CLOSED, 
                is_active=0,
                closed_at=datetime.utcnow(),
                closed_reason=r
            )
        )
        await session.commit()

    @staticmethod
    async def operator_join(session: AsyncSession, session_id: int, operator_tg_id: int):
        await session.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(
                operator_joined=True,
                operator_tg_id=operator_tg_id,
            )
        )
        # Cancel pending tasks
        await session.execute(
            update(BotTask)
            .where(
                BotTask.chat_session_id == session_id,
                BotTask.status == BotTaskStatus.PENDING,
            )
            .values(status=BotTaskStatus.DONE)
        )
        await session.commit()
