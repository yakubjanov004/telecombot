from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import ChatSession, SessionStatus, ClosedReason, TopicStatusEnum
from backend.adapters.telegram_adapter import TelegramAdapter
from backend.config import CHAT_GROUP_ID

logger = logging.getLogger(__name__)


class CleanupService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def cleanup_old_topics(self, days: int = 3) -> int:
        """Finds active sessions with no activity for 'days' and closes them."""
        # Normalize timezone-aware and timezone-naive values before comparing.
        threshold = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(ChatSession).where(
            ChatSession.status == SessionStatus.ACTIVE
        )
        result = await self.db.execute(stmt)
        active_sessions = result.scalars().all()
        
        sessions = []
        for s in active_sessions:
            ref_time = s.created_at or datetime.utcnow()
            client_act = s.last_client_message_at or ref_time
            operator_act = s.last_operator_message_at or ref_time
            bot_act = s.last_bot_message_at or ref_time
            
            # Ensure naive datetime comparison
            client_act_naive = client_act.replace(tzinfo=None) if client_act.tzinfo else client_act
            operator_act_naive = operator_act.replace(tzinfo=None) if operator_act.tzinfo else operator_act
            bot_act_naive = bot_act.replace(tzinfo=None) if bot_act.tzinfo else bot_act
            ref_time_naive = ref_time.replace(tzinfo=None) if ref_time.tzinfo else ref_time
            
            last_act = max(client_act_naive, operator_act_naive, bot_act_naive, ref_time_naive)
            if last_act <= threshold:
                sessions.append(s)
        
        if not sessions:
            return 0
            
        logger.info(f"CleanupService: Found {len(sessions)} sessions to cleanup (inactive for {days} days)")
        
        closed_count = 0
        tg = TelegramAdapter()
        for session in sessions:
            try:
                session.is_active = 0
                session.status = SessionStatus.CLOSED
                session.closed_at = datetime.utcnow()
                session.closed_reason = ClosedReason.TIMEOUT
                session.topic_status = TopicStatusEnum.EXPIRED
                
                topic_id = session.telegram_topic_id
                session.telegram_topic_id = None
                
                # Delete forum topic
                if topic_id and CHAT_GROUP_ID:
                    try:
                        await tg.delete_forum_topic(int(CHAT_GROUP_ID), int(topic_id))
                    except Exception as tg_err:
                        logger.warning(f"Could not delete forum topic {topic_id}: {tg_err}")
                
                closed_count += 1
            except Exception as e:
                logger.error(f"Failed to cleanup session {session.id}: {str(e)}")
                
        await self.db.commit()
        logger.info(f"CleanupService: Successfully closed {closed_count} topics automatically.")
        return closed_count
