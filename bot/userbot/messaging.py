"""Operator xabarlarini yuborish."""
import logging

from backend.services.simulation_helpers import split_message

logger = logging.getLogger(__name__)


async def send_operator_messages(
    userbot_app,
    chat_id: int,
    topic_id: int,
    text: str,
    *,
    night: bool = False,
    scenario_index: int = 0,
) -> None:
    """Xabarlarni sun'iy kechiktirmasdan yuborish."""
    parts = split_message(text, scenario_index=scenario_index)
    for part in parts:
        await userbot_app.send_message(
            chat_id=chat_id,
            text=part,
            reply_to_message_id=topic_id,
        )
