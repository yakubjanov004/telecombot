import aiohttp
import os
import json
import logging
import asyncio
import socket
from typing import Optional, Any
from backend.config import BOT_TOKEN, CHAT_GROUP_ID

logger = logging.getLogger(__name__)


class TelegramAdapter:
    _session: Optional[aiohttp.ClientSession] = None

    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.chat_group_id = int(CHAT_GROUP_ID)
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            connector = aiohttp.TCPConnector(family=socket.AF_INET, limit=100, use_dns_cache=True)
            timeout = aiohttp.ClientTimeout(total=60, connect=15, sock_read=45)
            cls._session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return cls._session

    @classmethod
    async def close_session(cls):
        if cls._session and not cls._session.closed:
            await cls._session.close()

    def _extract_retry_after(self, resp_text: str) -> int:
        try:
            data = json.loads(resp_text)
            return int(data.get("parameters", {}).get("retry_after", 0) or 0)
        except Exception:
            return 0

    async def create_forum_topic(self, topic_name: str) -> Optional[int]:
        try:
            session = await self.get_session()
            payload = {"chat_id": self.chat_group_id, "name": topic_name, "icon_color": 0x6FB9F0}
            
            async with session.post(f"{self.api_url}/createForumTopic", json=payload) as response:
                resp_text = await response.text()
                
                # Handle Rate Limiting for topic creation too
                if response.status == 429:
                    retry_after = self._extract_retry_after(resp_text)
                    if retry_after > 0:
                        logger.warning(f"Topic creation rate limited. Waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        async with session.post(f"{self.api_url}/createForumTopic", json=payload) as retry_resp:
                            resp_text = await retry_resp.text()
                            response = retry_resp

                if response.status != 200:
                    logger.error(f"Topic create error ({response.status}): {resp_text[:200]}")
                    return None
                
                result = json.loads(resp_text)
                if not result.get("ok"):
                    logger.error(f"TELEGRAM ERROR topic: {result}")
                    return None
                return result.get("result", {}).get("message_thread_id")
        except Exception as e:
            logger.error(f"Topic create exception: {e}")
            return None

    async def _clear_previous_markup(self, previous_message_id: int, message_thread_id: Optional[int]) -> None:
        try:
            session = await self.get_session()
            edit_payload = {
                "chat_id": self.chat_group_id,
                "message_id": previous_message_id,
                "reply_markup": {"inline_keyboard": []},
            }
            if message_thread_id is not None:
                edit_payload["message_thread_id"] = message_thread_id
            
            async with session.post(f"{self.api_url}/editMessageReplyMarkup", json=edit_payload) as edit_resp:
                if edit_resp.status not in (200, 429):
                    r_text = await edit_resp.text()
                    # Suppress 'message is not modified' error as it is harmless
                    if "message is not modified" not in r_text:
                        logger.warning(f"EDIT MARKUP ERROR ({edit_resp.status}): {r_text[:100]}")
        except Exception as e:
            logger.warning(f"Failed to edit previous message markup: {e}")

    async def send_message_with_error(
        self,
        text: str,
        message_thread_id: Optional[int] = None,
        reply_markup: Optional[dict] = None,
        previous_message_id: Optional[int] = None,
    ) -> tuple[Optional[int], Optional[str]]:
        try:
            payload = {
                "chat_id": self.chat_group_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            if message_thread_id:
                payload["message_thread_id"] = message_thread_id
            if reply_markup:
                payload["reply_markup"] = reply_markup

            session = await self.get_session()
            async with session.post(f"{self.api_url}/sendMessage", json=payload) as response:
                resp_text = await response.text()
                
                if response.status == 429:
                    retry_after = self._extract_retry_after(resp_text)
                    if retry_after > 0:
                        logger.warning(f"Rate limited. Retrying after {retry_after}s")
                        await asyncio.sleep(retry_after)
                        async with session.post(f"{self.api_url}/sendMessage", json=payload) as retry_resp:
                            resp_text = await retry_resp.text()
                            response = retry_resp

                if response.status != 200:
                    logger.error(f"TELEGRAM ERROR ({response.status}): {resp_text[:300]}")
                    return None, resp_text
                
                result = json.loads(resp_text)
                if not result.get("ok"):
                    return None, result.get("description") or resp_text
                
                msg_id = result.get("result", {}).get("message_id")
                if msg_id and previous_message_id:
                    asyncio.create_task(self._clear_previous_markup(previous_message_id, message_thread_id))
                return msg_id, None
        except Exception as e:
            logger.error(f"Send message exception: {e}")
            return None, str(e)

    async def send_message(self, text: str, message_thread_id: Optional[int] = None, reply_markup: Optional[dict] = None, previous_message_id: Optional[int] = None) -> Optional[int]:
        msg_id, _ = await self.send_message_with_error(text, message_thread_id=message_thread_id, reply_markup=reply_markup, previous_message_id=previous_message_id)
        return msg_id

    async def send_photo_with_error(
        self,
        photo_url: str,
        caption: Optional[str] = None,
        message_thread_id: Optional[int] = None,
        reply_markup: Optional[dict] = None
    ) -> tuple[Optional[int], Optional[str]]:
        try:
            session = await self.get_session()
            is_local = False
            if os.path.exists(photo_url):
                if os.path.isabs(photo_url) or (not photo_url.startswith('http')):
                    is_local = True

            if is_local:
                data = aiohttp.FormData()
                data.add_field("chat_id", str(self.chat_group_id))
                
                with open(photo_url, "rb") as f:
                    photo_data = f.read()
                    
                data.add_field("photo", photo_data, filename=os.path.basename(photo_url))
                
                if caption:
                    data.add_field("caption", caption)
                data.add_field("parse_mode", "HTML")
                if message_thread_id:
                    data.add_field("message_thread_id", str(message_thread_id))
                if reply_markup:
                    data.add_field("reply_markup", json.dumps(reply_markup))
                
                async with session.post(f"{self.api_url}/sendPhoto", data=data) as response:
                    resp_text = await response.text()
                    if response.status != 200:
                        logger.error(f"TG Photo Upload Error ({response.status}): {resp_text[:300]}")
                        return None, resp_text
                    result = json.loads(resp_text)
                    return result.get("result", {}).get("message_id"), None

            payload = {
                "chat_id": self.chat_group_id,
                "photo": photo_url,
                "caption": caption,
                "parse_mode": "HTML"
            }
            if message_thread_id:
                payload["message_thread_id"] = message_thread_id
            if reply_markup:
                payload["reply_markup"] = reply_markup

            async with session.post(f"{self.api_url}/sendPhoto", json=payload) as response:
                resp_text = await response.text()
                
                if response.status == 429:
                    retry_after = self._extract_retry_after(resp_text)
                    if retry_after > 0:
                        await asyncio.sleep(retry_after)
                        async with session.post(f"{self.api_url}/sendPhoto", json=payload) as retry_resp:
                            resp_text = await retry_resp.text()
                            response = retry_resp

                if response.status != 200:
                    logger.error(f"TG Photo Error ({response.status}): {resp_text[:300]}")
                    return None, resp_text
                    
                result = json.loads(resp_text)
                return result.get("result", {}).get("message_id"), None
        except Exception as e:
            logger.error(f"Send photo exception: {e}")
            return None, str(e)

    async def send_photo(
        self,
        photo_url: str,
        caption: Optional[str] = None,
        message_thread_id: Optional[int] = None,
        reply_markup: Optional[dict] = None
    ) -> Optional[int]:
        msg_id, _ = await self.send_photo_with_error(
            photo_url=photo_url,
            caption=caption,
            message_thread_id=message_thread_id,
            reply_markup=reply_markup,
        )
        return msg_id

    async def check_topic_exists(self, topic_id: int) -> bool:
        return True

    async def delete_forum_topic(self, topic_id: int) -> bool:
        try:
            session = await self.get_session()
            async with session.post(
                f"{self.api_url}/deleteForumTopic",
                json={"chat_id": self.chat_group_id, "message_thread_id": int(topic_id)},
            ) as response:
                if response.status != 200:
                    resp_text = await response.text()
                    logger.error(f"Delete topic error ({response.status}): {resp_text[:200]}")
                    return False
                data = await response.json()
                return bool(data.get("ok"))
        except Exception as e:
            logger.error(f"Delete topic exception: {e}")
            return False

    async def pin_chat_message(self, message_id: int) -> bool:
        try:
            session = await self.get_session()
            async with session.post(
                f"{self.api_url}/pinChatMessage",
                json={
                    "chat_id": self.chat_group_id,
                    "message_id": message_id,
                    "disable_notification": True
                }
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Pin message exception: {e}")
            return False

    async def answer_callback_query(self, callback_query_id: str, text: str, show_alert: bool = False):
        try:
            session = await self.get_session()
            await session.post(
                f"{self.api_url}/answerCallbackQuery",
                json={"callback_query_id": callback_query_id, "text": text, "show_alert": show_alert}
            )
        except Exception as e:
            logger.error(f"Answer callback error: {e}")
