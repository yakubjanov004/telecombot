import json
import logging
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models import BotTask, BotTaskType, BotTaskStatus

logger = logging.getLogger(__name__)


class BotTaskService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def add_task(self, session_id: int, task_type: BotTaskType, 
                       payload: dict = None, priority: int = 0, 
                       scheduled_at: datetime = None) -> Optional[BotTask]:
        """Adds a technical task to the queue for background processing (UTC-aware)."""
        try:
            now_utc = datetime.now(timezone.utc)
            payload = payload or {}

            # Bir sessiyada bir vaqtning o'zida faqat bitta PENDING — ketma-ketlik buzilmasin
            pending_res = await self.db.execute(
                select(BotTask).where(
                    BotTask.chat_session_id == session_id,
                    BotTask.task_type == task_type,
                    BotTask.status == BotTaskStatus.PENDING,
                )
            )
            existing = pending_res.scalar_one_or_none()
            if existing:
                # payload is stored as serialized JSON text
                try:
                    merged = json.loads(existing.payload) if existing.payload else {}
                except Exception:
                    merged = {}
                merged.update(payload)
                existing.payload = json.dumps(merged)
                existing.scheduled_at = scheduled_at or now_utc
                return existing

            task = BotTask(
                chat_session_id=session_id,
                task_type=task_type,
                status=BotTaskStatus.PENDING,
                payload=json.dumps(payload),
                priority=priority,
                scheduled_at=scheduled_at or now_utc,
                created_at=now_utc
            )
            self.db.add(task)
            return task
        except Exception as e:
            logger.error(f"Failed to add bot task {task_type} for session {session_id}: {str(e)}")
            return None

    async def update_task_status(self, task_id: int, status: BotTaskStatus, error_log: str = None):
        """Updates the status and processed timestamp of a task (UTC-aware)."""
        stmt = select(BotTask).where(BotTask.id == task_id)
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if task:
            task.status = status
            task.processed_at = datetime.now(timezone.utc)
            if error_log: 
                task.error_log = error_log
            await self.db.commit()
