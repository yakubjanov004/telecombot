import asyncio
import logging
import random
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal
from backend.models import BotTask, BotTaskStatus, BotTaskType, UserbotState, ChatSession, WaitingFor, SessionEventType, ClientMode
from bot.userbot.processor import ScenarioProcessor
from bot.userbot.client import get_userbot
from bot.core.loader import bot
import backend.config as settings
from bot.userbot.messaging import send_operator_messages
from backend.services.simulation_helpers import is_night_time

logger = logging.getLogger(__name__)

processor = ScenarioProcessor(settings.SCENARIOS_DIR)


async def process_tasks():
    async with AsyncSessionLocal() as db_session:
        result = await db_session.execute(
            select(BotTask)
            .where(BotTask.status == BotTaskStatus.PENDING)
            .order_by(BotTask.priority.desc(), BotTask.id.asc())
            .limit(10)
        )
        tasks = result.scalars().all()

        if not tasks:
            return

        userbot_app = await get_userbot()

        for task in tasks:
            try:
                task.status = BotTaskStatus.PROCESSING
                await db_session.commit()
                
                # Get session
                chat_session = await db_session.get(ChatSession, task.chat_session_id)
                if not chat_session or chat_session.operator_joined:
                    task.status = BotTaskStatus.DONE
                    await db_session.commit()
                    continue

                # Get or create state
                state_res = await db_session.execute(
                    select(UserbotState).where(UserbotState.chat_session_id == chat_session.id)
                )
                state = state_res.scalars().first()
                if not state:
                    # Pick a random scenario index once at the start of the session
                    service_type = chat_session.service_type.value if chat_session.service_type else "internet"
                    count = processor.get_variant_count(service_type)
                    idx = random.randint(0, count - 1) if count > 0 else 0
                    
                    initial_step = (
                        "start"
                        if chat_session.client_mode and chat_session.client_mode.value == "simulated"
                        else "greeting"
                    )
                    state = UserbotState(
                        chat_session_id=chat_session.id,
                        current_step=initial_step,
                        collected_data=json.dumps({}),
                        waiting_for=WaitingFor.CLIENT,
                        scenario_index=idx,
                    )
                    db_session.add(state)
                    await db_session.flush()

                response_text = ""
                next_step = state.current_step
                service_type = chat_session.service_type.value if chat_session.service_type else "internet"
                if chat_session.client_mode and chat_session.client_mode.value == "simulated":
                    service_type = "internet"
                action = None

                try:
                    collected = json.loads(state.collected_data) if state.collected_data else {}
                except Exception:
                    collected = {}

                # Decode serialized task payload if needed
                try:
                    task_payload = json.loads(task.payload) if task.payload else {}
                except Exception:
                    task_payload = {}

                if task.task_type == BotTaskType.SEND_INTRO:
                    res = processor.get_operator_greeting(service_type, scenario_index=state.scenario_index)
                    response_text = res["response"]
                    next_step = res["next_step"]
                
                elif task.task_type == BotTaskType.SEND_SCENARIO_STEP:
                    from backend.services.session_sale_service import ensure_msisdn_from_db

                    collected = await ensure_msisdn_from_db(db_session, collected)
                    state.collected_data = json.dumps(collected)
                    
                    text_input = task_payload.get("text")
                    intent = task_payload.get("intent")
                    if text_input and not intent:
                        intent = processor.detect_intent(
                            service_type,
                            text_input,
                            scenario_index=state.scenario_index,
                            current_step=state.current_step,
                        )
                    res = processor.process_operator_step(
                        service_type,
                        state.current_step,
                        intent,
                        text_input,
                        collected,
                        scenario_index=state.scenario_index
                    )
                    response_text = res["response"]
                    next_step = res["next_step"]
                    action = res.get('action')
                    collected = res.get("collected_data", collected)
                    state.collected_data = json.dumps(collected)

                    if next_step == "processing":
                        from backend.services.session_sale_service import (
                            persist_wifi_sale_from_session,
                        )
                        await persist_wifi_sale_from_session(
                            db_session,
                            chat_session,
                            collected,
                            operator_tg_id=chat_session.operator_tg_id,
                        )

                if response_text:
                    if userbot_app and userbot_app.is_connected:
                        try:
                            await send_operator_messages(
                                userbot_app,
                                int(settings.SUPPORT_GROUP_ID),
                                chat_session.telegram_topic_id,
                                response_text,
                                night=is_night_time(),
                                scenario_index=state.scenario_index or 0,
                            )
                            if chat_session.client_mode == ClientMode.REAL and chat_session.client_tg_id:
                                await bot.send_message(chat_session.client_tg_id, response_text)
                            
                            from backend.services.chat_session_service import ChatSessionService
                            session_service = ChatSessionService(db_session)
                            await session_service.log_event(chat_session.id, SessionEventType.BOT_MESSAGE_SENT, {"auto": True})
                            await session_service.update_activity(chat_session.id, 'bot')
                        except Exception as e:
                            if "TOPIC_CLOSED" in str(e):
                                logger.warning(f"Userbot auto-reply skip: Topic {chat_session.telegram_topic_id} in session {chat_session.id} is already closed.")
                                task.status = BotTaskStatus.DONE
                                await db_session.commit()
                                continue
                            else:
                                logger.error(f"Userbot auto-reply send error: {e}")
                                state.waiting_for = WaitingFor.CLIENT

                    if action == 'handoff':
                        chat_session.operator_joined = True
                        chat_session.userbot_active = False

                state.current_step = next_step
                if not action == 'handoff' and not next_step == 'completed':
                    state.waiting_for = WaitingFor.CLIENT
                else:
                    state.waiting_for = WaitingFor.NONE

                task.status = BotTaskStatus.DONE
                await db_session.commit()
                logger.info(f"Task {task.id} processed for session {chat_session.id}")

            except Exception as e:
                logger.error(f"Task {task.id} processing error: {e}", exc_info=True)
                task.status = BotTaskStatus.FAILED
                task.error_log = str(e)
                try:
                    await db_session.commit()
                except:
                    pass


async def worker_loop():
    logger.info("Userbot Auto-Operator worker started...")
    while True:
        try:
            await process_tasks()
        except Exception as e:
            logger.error(f"Error in worker_loop: {e}")
        await asyncio.sleep(0.3)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    asyncio.run(worker_loop())
