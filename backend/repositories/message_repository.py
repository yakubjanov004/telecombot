from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from backend.models import ChatMessage


class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, session_id: str, sender: str, message: str, media_url: Optional[str] = None) -> ChatMessage:
        msg = ChatMessage(session_id=session_id, sender=sender, message=message, media_url=media_url)
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def get_by_session(self, session_id: str) -> List[ChatMessage]:
        result = await self.db.execute(select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at))
        return result.scalars().all()

    async def get_last_by_sender(self, session_id: str, sender: str) -> Optional[ChatMessage]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.sender == sender)
            .order_by(desc(ChatMessage.created_at))
            .limit(1)
        )
        return result.scalars().first()
