from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
import json

from backend.models import BotTask, BotTaskStatus, BotTaskType, UserbotState, ChatSession


class AutoOperatorRepo:
    @staticmethod
    async def enqueue_task(
        session: AsyncSession,
        chat_session_id: int,
        task_type: BotTaskType,
        payload: dict | None = None,
        priority: int = 0,
    ):
        task = BotTask(
            chat_session_id=chat_session_id,
            task_type=task_type,
            status=BotTaskStatus.PENDING,
            payload=json.dumps(payload or {}),
            priority=priority,
        )
        session.add(task)
        await session.commit()
        return task

    @staticmethod
    async def mark_pending_processed_by_session(
        session: AsyncSession, chat_session_id: int
    ):
        await session.execute(
            update(BotTask)
            .where(
                BotTask.chat_session_id == chat_session_id,
                BotTask.status.in_([BotTaskStatus.PENDING, BotTaskStatus.PROCESSING]),
            )
            .values(status=BotTaskStatus.DONE, processed_at=func.now())
        )
        await session.commit()


class UserbotStateRepo:
    @staticmethod
    async def get_by_session(
        session: AsyncSession, chat_session_id: int
    ) -> UserbotState | None:
        result = await session.execute(
            select(UserbotState).where(
                UserbotState.chat_session_id == chat_session_id
            )
        )
        return result.scalars().first()

    @staticmethod
    async def delete_by_session(session: AsyncSession, chat_session_id: int):
        await session.execute(
            delete(UserbotState).where(UserbotState.chat_session_id == chat_session_id)
        )
        await session.commit()
