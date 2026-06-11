from fastapi import WebSocket
from typing import Dict, List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        sockets = self.connections.setdefault(session_id, [])
        if websocket not in sockets:
            sockets.append(websocket)

    def disconnect(self, session_id: str, websocket: Optional[WebSocket] = None):
        sockets = self.connections.get(session_id)
        if not sockets:
            return
        if websocket is None:
            self.connections.pop(session_id, None)
            return
        if websocket in sockets:
            sockets.remove(websocket)
        if not sockets:
            self.connections.pop(session_id, None)

    async def send_json(self, session_id: str, data: dict, websocket: Optional[WebSocket] = None) -> bool:
        if websocket is not None:
            try:
                await websocket.send_json(data)
                return True
            except Exception as exc:
                logger.debug("WebSocket send failed for %s: %s", session_id, exc)
                self.disconnect(session_id, websocket)
                return False

        sockets = list(self.connections.get(session_id, []))
        if not sockets:
            return False

        delivered = False
        for ws in sockets:
            try:
                await ws.send_json(data)
                delivered = True
            except Exception as exc:
                logger.debug("WebSocket send failed for %s: %s", session_id, exc)
                self.disconnect(session_id, ws)
        return delivered

    async def send_message(self, session_id: str, sender: str, message: str, media_url: Optional[str] = None, from_server: bool = False) -> bool:
        return await self.send_json(session_id, {
            "type": "message", 
            "sender": sender, 
            "message": message, 
            "media_url": media_url,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), 
            "from_server": from_server
        })


ws_manager = WebSocketManager()
