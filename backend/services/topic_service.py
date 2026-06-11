from pathlib import Path
from typing import Optional, Union
import logging
from aiogram import Bot
from aiogram.types import FSInputFile

import backend.config as settings

logger = logging.getLogger(__name__)


class TopicService:
    def __init__(self, bot: Bot, group_id: int = None):
        self.bot = bot
        self.group_id = group_id or int(settings.SUPPORT_GROUP_ID)

    async def create_topic(self, name: str) -> Optional[int]:
        """Creates a forum topic in a supergroup."""
        try:
            result = await self.bot.create_forum_topic(
                chat_id=self.group_id,
                name=name
            )
            return result.message_thread_id
        except Exception as e:
            logger.error(f"Failed to create topic '{name}': {str(e)}")
            return None

    async def close_topic(self, thread_id: int):
        """Closes a forum topic."""
        try:
            await self.bot.close_forum_topic(
                chat_id=self.group_id,
                message_thread_id=thread_id
            )
            logger.info(f"Topic {thread_id} closed successfully.")
        except Exception as e:
            logger.error(f"Failed to close topic {thread_id}: {str(e)}")

    async def send_message(self, thread_id: int, text: str, pin: bool = False):
        """Sends a message to a topic and optionally pins it with error handling."""
        try:
            msg = await self.bot.send_message(
                chat_id=self.group_id,
                text=text,
                message_thread_id=thread_id
            )
            
            if pin and msg:
                try:
                    await self.bot.pin_chat_message(
                        chat_id=self.group_id,
                        message_id=msg.message_id
                    )
                    logger.info(f"Message {msg.message_id} pinned in topic {thread_id}")
                except Exception as pin_err:
                    logger.warning(f"Failed to pin message {msg.message_id} in topic {thread_id}: {pin_err}")
                    
            return msg.message_id
        except Exception as e:
            logger.error(f"Failed to send message to topic {thread_id}: {str(e)}")
            return None

    async def send_voice(
        self,
        thread_id: int,
        audio_path: Union[str, Path],
    ) -> Optional[int]:
        """Mijoz (sim) ovozli xabari."""
        try:
            msg = await self.bot.send_voice(
                chat_id=self.group_id,
                voice=FSInputFile(str(audio_path)),
                message_thread_id=thread_id,
            )
            return msg.message_id
        except Exception as e:
            logger.warning("Failed to send voice to topic %s: %s", thread_id, e)
            return None
