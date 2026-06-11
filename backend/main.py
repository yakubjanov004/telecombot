import os
import sys
import asyncio
from datetime import datetime
import json
import logging
import uuid
import shutil
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks, File, UploadFile, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import engine, get_db, AsyncSessionLocal
from backend.models import Base, ClosedReason, SessionStatus, TopicStatusEnum, ServiceType
from backend.schemas import InternetApplicationCreate, InternetApplicationResponse, MobileApplicationCreate, MobileApplicationResponse, SessionCreate, OperatorMessage
from backend.services.application_service import ApplicationService
from backend.services.chat_service import ChatService
from backend.adapters.websocket_manager import ws_manager
from backend.adapters.telegram_adapter import TelegramAdapter
from backend.config import APP_HOST, APP_PORT, CHAT_GROUP_ID, BOT_TOKEN, UPLOAD_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ariza & Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/api/uploads", StaticFiles(directory=UPLOAD_DIR), name="api_uploads")


async def download_telegram_file(file_id: str):
    if not file_id:
        return None
    try:
        adapter = TelegramAdapter()
        session = await TelegramAdapter.get_session()
        async with session.get(f"{adapter.api_url}/getFile", params={"file_id": file_id}) as response:
            if response.status != 200:
                logger.error(f"getFile error ({response.status})")
                return None
            data = await response.json()
            if not data.get("ok"):
                logger.error(f"getFile response not ok: {data}")
                return None
            file_path = data.get("result", {}).get("file_path")
            if not file_path:
                return None

        file_ext = os.path.splitext(file_path)[1] or ".jpg"
        file_name = f"{uuid.uuid4().hex}{file_ext}"
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        local_path = os.path.join(UPLOAD_DIR, file_name)

        async with session.get(file_url) as file_resp:
            if file_resp.status != 200:
                logger.error(f"File download error ({file_resp.status})")
                return None
            content = await file_resp.read()

        with open(local_path, "wb") as f:
            f.write(content)

        return f"/uploads/{file_name}"
    except Exception as e:
        logger.error(f"Download telegram file error: {e}")
        return None


@app.on_event("startup")
async def startup():
    from backend.migrations import migrate_schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(migrate_schema)
    await TelegramAdapter.get_session()


@app.on_event("shutdown")
async def shutdown():
    await TelegramAdapter.close_session()
    await engine.dispose()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    try:
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Faqat rasmlar qabul qilinadi")
            
        file_ext = os.path.splitext(file.filename)[1]
        file_name = f"{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {"url": f"/uploads/{file_name}"}
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Fayl yuklashda xatolik")


def _load_tariffs_from_assets(service_type: Optional[str] = None) -> list:
    assets_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "assets",
        "tariffs.json",
    )
    try:
        with open(assets_path, encoding="utf-8") as f:
            data = json.load(f)
        tariffs = data.get("tariffs", [])
        if service_type:
            tariffs = [t for t in tariffs if t.get("service_type") == service_type]
        return tariffs
    except Exception as e:
        logger.warning("Failed to load tariffs from assets: %s", e)
        return []


@app.get("/api/tariffs")
async def list_tariffs(type: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    from backend.models import RatePlan, ServiceType
    from sqlalchemy import select

    assets_tariffs = _load_tariffs_from_assets(type)
    assets_by_name = {t["name"]: t for t in assets_tariffs}

    stype = None
    if type == "internet":
        stype = ServiceType.INTERNET
    elif type == "mobile":
        stype = ServiceType.MOBILE

    plans = []
    if type != "mail":
        stmt = select(RatePlan).where(RatePlan.is_active == True)
        if stype:
            stmt = stmt.where(RatePlan.service_type == stype)
        res = await db.execute(stmt)
        plans = res.scalars().all()

    if not plans:
        return assets_tariffs

    result = []
    for p in plans:
        asset = assets_by_name.get(p.name, {})
        result.append({
            "id": p.id,
            "name": p.name,
            "service_type": p.service_type.value if hasattr(p.service_type, "value") else str(p.service_type),
            "group": asset.get("group"),
            "price": p.price or asset.get("price") or (70000 if p.service_type == ServiceType.INTERNET else 35000),
            "description": p.description or asset.get("description") or "",
            "speed": p.speed or asset.get("speed") or "",
            "minutes": p.minutes or asset.get("minutes") or "",
            "sms": p.sms or asset.get("sms") or "",
            "mb": p.mb or asset.get("mb") or "",
        })
    return result


@app.post("/api/applications/internet", response_model=InternetApplicationResponse)
async def create_internet_application(data: InternetApplicationCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        service = ApplicationService(db)
        app_obj = await service.create_internet(
            branches=data.branches,
            departments=data.departments,
            navi_user=data.navi_user,
            rt_lc_states=data.rt_lc_states,
            msisdn=data.msisdn,
            rate_plan_first_connection=data.rate_plan_first_connection,
            selected_tariff_id=data.selected_tariff_id,
            selected_tariff_code=data.selected_tariff_code,
        )
        async def notify():
            async with AsyncSessionLocal() as db2:
                chat = ChatService(db2)
                await chat.notify_internet_app(
                    app_obj.id,
                    app_obj.branches,
                    app_obj.departments,
                    app_obj.navi_user,
                    app_obj.rt_lc_states,
                    app_obj.msisdn,
                    app_obj.rate_plan_first_connection,
                    app_obj.created_at,
                )
        background_tasks.add_task(notify)
        return InternetApplicationResponse(
            id=app_obj.id, 
            city=app_obj.city, 
            first_name=app_obj.first_name, 
            last_name=app_obj.last_name, 
            father_name=app_obj.father_name, 
            status=app_obj.status.value, 
            created_at=app_obj.created_at, 
            updated_at=app_obj.updated_at, 
            done_at=app_obj.done_at,
            phone=app_obj.phone,
            selected_tariff_id=app_obj.selected_tariff_id,
            selected_tariff_code=app_obj.selected_tariff_code,
            address=app_obj.address,
            branches=app_obj.branches,
            departments=app_obj.departments,
            navi_user=app_obj.navi_user,
            rt_lc_states=app_obj.rt_lc_states,
            msisdn=app_obj.msisdn,
            rate_plan_first_connection=app_obj.rate_plan_first_connection,
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Xatolik yuz berdi")


@app.post("/api/applications/mobile", response_model=MobileApplicationResponse)
async def create_mobile_application(data: MobileApplicationCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        service = ApplicationService(db)
        app_obj = await service.create_mobile(
            dealer=data.dealer,
            navi_user=data.navi_user,
            msisdn=data.msisdn,
            rate_plan_first_connection=data.rate_plan_first_connection,
            branches=data.branches,
            selected_tariff_id=data.selected_tariff_id,
            selected_tariff_code=data.selected_tariff_code,
        )
        async def notify():
            async with AsyncSessionLocal() as db2:
                chat = ChatService(db2)
                await chat.notify_mobile_app(
                    app_obj.id,
                    app_obj.dealer,
                    app_obj.navi_user,
                    app_obj.msisdn,
                    app_obj.rate_plan_first_connection,
                    app_obj.branches,
                    app_obj.created_at,
                )
        background_tasks.add_task(notify)
        return MobileApplicationResponse(
            id=app_obj.id, 
            phone=app_obj.phone, 
            operator_code=app_obj.operator_code, 
            first_name=app_obj.first_name, 
            last_name=app_obj.last_name, 
            father_name=app_obj.father_name, 
            status=app_obj.status.value, 
            created_at=app_obj.created_at, 
            updated_at=app_obj.updated_at, 
            done_at=app_obj.done_at,
            selected_tariff_id=app_obj.selected_tariff_id,
            selected_tariff_code=app_obj.selected_tariff_code,
            address=app_obj.address,
            dealer=app_obj.dealer,
            navi_user=app_obj.navi_user,
            msisdn=app_obj.msisdn,
            rate_plan_first_connection=app_obj.rate_plan_first_connection,
            branches=app_obj.branches,
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Xatolik yuz berdi")


@app.post("/api/sessions")
async def create_session(data: SessionCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        chat = ChatService(db)
        result = await chat.get_or_create_session(data.session_id, data.client_name, data.phone, data.application_type, data.application_id)
        session_id = result["session_id"]
        
        async def bg_task():
            try:
                async with AsyncSessionLocal() as db_bg:
                    chat_bg = ChatService(db_bg)
                    lock = chat_bg.get_lock(session_id)
                    async with lock:
                        await chat_bg.create_topic(session_id, data.client_name, data.application_type, data.application_id)
            except Exception as e:
                logger.error(f"Background topic creation error: {e}")
        
        background_tasks.add_task(bg_task)
        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Xatolik yuz berdi")


@app.get("/api/sessions")
async def list_sessions(only_active: bool = True, db: AsyncSession = Depends(get_db)):
    chat = ChatService(db)
    return await chat.list_sessions(only_active)


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    chat = ChatService(db)
    result = await chat.get_session_with_messages(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@app.post("/api/sessions/{session_id}/close")
async def close_client_session(session_id: str, db: AsyncSession = Depends(get_db)):
    chat = ChatService(db)
    session = await chat.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.is_active or session.status == SessionStatus.CLOSED:
        return {"status": "closed", "message": "Session already closed"}

    topic_id = session.telegram_topic_id
    session.status = SessionStatus.CLOSED
    session.is_active = 0
    session.topic_status = TopicStatusEnum.EXPIRED
    session.closed_at = datetime.utcnow()
    session.closed_reason = ClosedReason.CANCELLED
    await db.commit()

    await ws_manager.send_json(
        session_id,
        {
            "type": "system",
            "status": "expired",
            "message": "Chat tugatildi. Yangi ariza berishingiz mumkin.",
        },
    )

    if topic_id:
        try:
            await TelegramAdapter().delete_forum_topic(int(topic_id))
        except Exception as exc:
            logger.warning("Could not delete forum topic %s: %s", topic_id, exc)

    return {"status": "closed", "message": "Chat closed"}


async def _close_websocket(websocket: WebSocket):
    try:
        await websocket.close()
    except RuntimeError:
        pass


@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await ws_manager.connect(session_id, websocket)
    try:
        async with AsyncSessionLocal() as db:
            chat = ChatService(db)
            session = await chat.get_session(session_id)
            if not session:
                await ws_manager.send_json(session_id, {"type": "error", "message": "Session not found"}, websocket=websocket)
                await _close_websocket(websocket)
                return
            if (not session.is_active) or session.topic_status in [TopicStatusEnum.EXPIRED, TopicStatusEnum.DELETED]:
                await ws_manager.send_json(session_id, {"type": "system", "status": "expired", "message": "Chat sessiyasi tugagan. Yangi ariza bering."}, websocket=websocket)
                await _close_websocket(websocket)
                return
            messages = await chat.get_messages(session_id)
            for m in messages:
                await ws_manager.send_json(session_id, {
                    "type": "message", 
                    "sender": m.sender, 
                    "message": m.message, 
                    "media_url": m.media_url,
                    "timestamp": f"{m.created_at.isoformat()}Z" if m.created_at else None, 
                    "from_server": True
                }, websocket=websocket)
            
            if not messages:
                await chat.send_welcome_message(session_id)
        
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except Exception:
                continue
            if data.get("type") != "message":
                continue
            client_msg = (data.get("message") or "").strip()
            media_url = data.get("media_url")
            if not client_msg and not media_url:
                continue
            async with AsyncSessionLocal() as db:
                chat = ChatService(db)
                session = await chat.get_session(session_id)
                if not session:
                    await ws_manager.send_json(session_id, {"type": "error", "message": "Session not found"}, websocket=websocket)
                    continue
                result = await chat.send_client_message(session_id, client_msg, media_url=media_url)
                if not result.get("ok"):
                    if result.get("error") == "rate_limited":
                        retry_after = int(result.get("retry_after") or 5)
                        await ws_manager.send_json(session_id, {"type": "system", "status": "rate_limit", "retry_after": retry_after, "message": f"Iltimos {retry_after} soniya kuting."}, websocket=websocket)
                        continue
                    if result.get("error") == "session_not_found":
                        await ws_manager.send_json(session_id, {"type": "error", "message": "Session not found"}, websocket=websocket)
                        continue
                    await ws_manager.send_json(session_id, {"type": "error", "message": "Xatolik yuz berdi"}, websocket=websocket)
                    continue
    except WebSocketDisconnect:
        pass
    except RuntimeError as e:
        if "WebSocket is not connected" not in str(e):
            logger.error(f"WS error: {e}")
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        ws_manager.disconnect(session_id, websocket)


@app.post("/api/operator/message")
async def operator_message(data: OperatorMessage, db: AsyncSession = Depends(get_db)):
    chat = ChatService(db)
    session = await chat.get_session(data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if (not session.is_active) or session.topic_status in [TopicStatusEnum.EXPIRED, TopicStatusEnum.DELETED]:
        raise HTTPException(status_code=410, detail="Session expired")
    if data.message == "__operator_claimed__":
        online = await ws_manager.send_json(
            data.session_id,
            {
                "type": "system",
                "status": "claimed",
                "message": "Operator chatga ulandi. Javoblar shu yerga keladi.",
            },
        )
        return {"status": "success" if online else "sent", "message": "ok"}
    await chat.save_operator_message(data.session_id, data.message, media_url=data.media_url, skip_telegram=data.skip_telegram)
    online = await chat.send_to_client(data.session_id, data.message, media_url=data.media_url)
    return {"status": "success" if online else "sent", "message": "ok"}


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting backend server on {APP_HOST}:{APP_PORT}")
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
