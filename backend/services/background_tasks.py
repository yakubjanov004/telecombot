import asyncio
import logging
import random
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, update, delete
from backend.database import AsyncSessionLocal
from backend.models import User, ChatSession, SessionStatus, ClientMode, ServiceType, UserbotState, WaitingFor, BotTaskType, BotTask, BotTaskStatus, ClosedReason, InternetSale
from backend.services.cleanup_service import CleanupService
from backend.services.chat_session_service import ChatSessionService
from backend.services.bot_task_service import BotTaskService
from backend.services.topic_service import TopicService
from bot.core.loader import bot
import backend.config as settings
from bot.userbot.processor import ScenarioProcessor
from backend.services.simulation_helpers import (
    build_client_messages,
    is_night_time,
    seed_simulation_meta,
)
from backend.services.dialogue_profiles import should_processing_chatter
from backend.services.sound_profiles import client_wait_seconds, inter_message_delay, should_send_voice
from backend.services.voice_service import synthesize_voice

logger = logging.getLogger(__name__)
_scenario_processor = ScenarioProcessor(settings.SCENARIOS_DIR)

_WAITING_CHATTER = [
    "Aka, tez bo'l birozgina.",
    "Qachon tugaydi?",
    "Ok, kutayapman.",
    "Bo'ldimi?",
    "Jigar, ishlayaptimi baza?",
    "Kutib qoldim, qancha vaqt?",
    "Hozir kutyapman.",
    "Rahmat, kutaman.",
    "Jigar kutibturipman",
    "Tezroq yozvarsangiz zur bo'lardi.",
]

sim_state = {
    "current_load": "medium", 
    "next_rotation_at": None,
    "last_creation_at": None,
    "next_creation_in_sec": 0
}


def get_target_range():
    if sim_state["current_load"] == "low":
        return settings.FAKE_TARGET_LOW_MIN, settings.FAKE_TARGET_LOW_MAX
    elif sim_state["current_load"] == "peak":
        return settings.FAKE_TARGET_PEAK_MIN, settings.FAKE_TARGET_PEAK_MAX
    else:
        return settings.FAKE_TARGET_MEDIUM_MIN, settings.FAKE_TARGET_MEDIUM_MAX


async def cleanup_loop():
    """Loop to periodically cleanup old/inactive topics."""
    logger.info("Cleanup loop started (Interval: %ds)", settings.TOPIC_EXPIRY_CHECK_SEC)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                cleanup_service = CleanupService(db)
                closed_count = await cleanup_service.cleanup_old_topics(days=settings.TOPIC_AUTO_DELETE_DAYS)
                if closed_count > 0:
                    logger.info("Cleanup loop: Closed %d inactive sessions.", closed_count)
        except Exception as e:
            logger.error("Error in cleanup_loop: %s", e)
        
        await asyncio.sleep(settings.TOPIC_EXPIRY_CHECK_SEC)


async def fake_client_loop():
    """Advanced loop to generate realistic fake client traffic."""
    if not settings.FAKE_ENABLED:
        logger.info("Fake Client Engine is disabled.")
        return

    logger.info("Realistic Fake Client Engine started.")
    
    while True:
        try:
            now = datetime.utcnow()
            
            if not sim_state["next_rotation_at"] or now >= sim_state["next_rotation_at"]:
                sim_state["current_load"] = random.choice(["low", "medium", "peak"])
                rotate_mins = random.randint(settings.FAKE_TARGET_ROTATE_MIN_MINUTES, settings.FAKE_TARGET_ROTATE_MAX_MINUTES)
                sim_state["next_rotation_at"] = now + timedelta(minutes=rotate_mins)
                logger.info("Simulation Load rotated to: %s (Next in %d mins)", sim_state["current_load"], rotate_mins)

            async with AsyncSessionLocal() as db:
                chat_service = ChatSessionService(db)
                
                comp_limit = now - timedelta(minutes=settings.FAKE_COMPLETED_CLOSE_MIN)
                stale_stmt = select(ChatSession.id).join(UserbotState).where(
                    ChatSession.client_mode == ClientMode.SIMULATED,
                    ChatSession.status == SessionStatus.ACTIVE,
                    UserbotState.current_step == 'completed',
                    UserbotState.updated_at <= comp_limit
                )
                stale_res = await db.execute(stale_stmt)
                for sid in stale_res.scalars().all():
                    await chat_service.close_session(sid, ClosedReason.RESOLVED)
                
                timeout_limit = now - timedelta(minutes=settings.FAKE_STEP_TIMEOUT_MIN)
                timeout_stmt = select(ChatSession.id).join(UserbotState).where(
                    ChatSession.client_mode == ClientMode.SIMULATED,
                    ChatSession.status == SessionStatus.ACTIVE,
                    UserbotState.updated_at <= timeout_limit
                )
                timeout_res = await db.execute(timeout_stmt)
                for sid in timeout_res.scalars().all():
                    await chat_service.close_session(sid, ClosedReason.TIMEOUT)
                
                await db.commit()

                if is_night_time():
                    await asyncio.sleep(60)
                    continue

                target_min, target_max = get_target_range()
                
                active_stmt = select(func.count(ChatSession.id)).where(
                    ChatSession.client_mode == ClientMode.SIMULATED,
                    ChatSession.status == SessionStatus.ACTIVE
                )
                active_res = await db.execute(active_stmt)
                active_count = active_res.scalar() or 0
                
                if active_count < target_max:
                    if not sim_state["last_creation_at"] or now >= (sim_state["last_creation_at"] + timedelta(seconds=sim_state["next_creation_in_sec"])):
                        to_create = random.randint(1, settings.FAKE_CREATE_BURST_MAX)
                        created_now = 0
                        
                        for _ in range(to_create):
                            if active_count + created_now >= settings.FAKE_MAX_ACTIVE_SESSIONS:
                                break
                            
                            user_stmt = select(User).where(User.is_simulated == True).order_by(func.random()).limit(1)
                            users_res = await db.execute(user_stmt)
                            user = users_res.scalar_one_or_none()
                            if not user:
                                break
                            s_type = ServiceType.INTERNET

                            short_id = f"#{random.randint(100, 9999)}"

                            session = await chat_service.start_session(
                                client_tg_id=user.tg_id,
                                service_type=s_type,
                                client_name=short_id,
                                mode=ClientMode.SIMULATED
                            )
                            if session:
                                created_now += 1
                                logger.info("Fake Engine: Started session %d (%s) - [Count: %d/%d]", session.id, short_id, active_count + created_now, target_max)
                        
                        sim_state["last_creation_at"] = now
                        sim_state["next_creation_in_sec"] = random.randint(settings.FAKE_INTERVAL_MIN_SEC, settings.FAKE_INTERVAL_MAX_SEC)
                        logger.info("Fake Engine: Next creation in %d seconds.", sim_state["next_creation_in_sec"])

        except Exception as e:
            logger.error("Error in fake_client_loop: %s", e, exc_info=True)
            
        await asyncio.sleep(30) 


async def fake_client_reply_loop():
    """Simulates client replies with more variety and logic."""
    if not settings.FAKE_ENABLED:
        return

    logger.info("Realistic Fake Client Reply loop started.")
    
    while True:
        try:
             async with AsyncSessionLocal() as db:
                stmt = select(ChatSession, UserbotState).join(UserbotState).where(
                    ChatSession.client_mode == ClientMode.SIMULATED,
                    ChatSession.status == SessionStatus.ACTIVE,
                    UserbotState.waiting_for == WaitingFor.CLIENT
                )
                res = await db.execute(stmt)
                results = res.all()
                
                topic_service = TopicService(bot)
                task_service = BotTaskService(db)
                chat_service = ChatSessionService(db)

                for session, state in results:
                    s_idx = state.scenario_index or 0
                    night = is_night_time()
                    lo, hi = client_wait_seconds(s_idx, night=night)
                    wait_sec = random.randint(lo, hi)
                    
                    # Ensure timezone-aware state update time comparisons.
                    state_updated = state.updated_at
                    if state_updated.tzinfo is not None:
                        state_updated = state_updated.replace(tzinfo=None)
                    
                    now_naive = datetime.utcnow()
                    if now_naive - state_updated <= timedelta(seconds=wait_sec):
                        continue

                    s_type = "internet"

                    if random.randint(1, 100) <= 12:
                        await chat_service.close_session(session.id, ClosedReason.TIMEOUT)
                        logger.info("Fake Engine: Client abandoned session %d (closed).", session.id)
                        continue

                    try:
                        collected = json.loads(state.collected_data) if state.collected_data else {}
                    except Exception:
                        collected = {}
                    
                    collected = await seed_simulation_meta(db, collected, s_type)
                    state.collected_data = json.dumps(collected)
                    meta = collected.get("_meta", {})

                    use_chatter = state.current_step in (
                        "processing",
                        "completed",
                    ) and should_processing_chatter(s_idx)

                    if use_chatter:
                        client_msgs = [random.choice(_WAITING_CHATTER)]
                        processor_text = client_msgs[0]
                    else:
                        client_msgs, processor_text = build_client_messages(
                            state.current_step or "start",
                            meta,
                            s_type,
                            scenario_index=state.scenario_index or 0,
                        )

                    step_name = state.current_step or "start"
                    for i, msg in enumerate(client_msgs):
                        sent = False
                        if should_send_voice(s_idx, step_name):
                            audio = await synthesize_voice(msg, s_idx)
                            if audio:
                                sent = (
                                    await topic_service.send_voice(
                                        session.telegram_topic_id, audio
                                    )
                                    is not None
                                )
                        if not sent:
                            await topic_service.send_message(session.telegram_topic_id, msg)
                        if i < len(client_msgs) - 1:
                            await asyncio.sleep(inter_message_delay(s_idx))

                    intent = _scenario_processor.detect_intent(
                        s_type,
                        processor_text,
                        scenario_index=s_idx,
                        current_step=state.current_step,
                    )

                    state.waiting_for = WaitingFor.BOT
                    await task_service.add_task(
                        session_id=session.id,
                        task_type=BotTaskType.SEND_SCENARIO_STEP,
                        payload={
                            "trigger": "client_replied",
                            "text": processor_text,
                            "intent": intent,
                        },
                    )
                    logger.info(
                        "Fake Engine: Client replied for session %d (%s)",
                        session.id,
                        state.current_step,
                    )
                    await db.commit()

        except Exception as e:
            logger.error("Error in fake_client_reply_loop: %s", e, exc_info=True)
            
        await asyncio.sleep(5)
