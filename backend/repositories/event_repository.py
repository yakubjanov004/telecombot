from sqlalchemy.ext.asyncio import AsyncSession
import json
from backend.models import SessionEventLog, SessionEventType


class SessionEventLogRepo:
    @staticmethod
    async def log_event(
        session: AsyncSession,
        chat_session_id: int,
        event_type: SessionEventType,
        actor_tg_id: int | None = None,
        event_data: dict | None = None,
    ):
        event = SessionEventLog(
            chat_session_id=chat_session_id,
            event_type=event_type,
            actor_tg_id=actor_tg_id,
            event_data=json.dumps(event_data or {}),
        )
        session.add(event)
        await session.commit()
        return event
