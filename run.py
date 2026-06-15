import asyncio
import logging
import os
import socket
import sys
import uvicorn
from dotenv import load_dotenv

# Ensure root of main/ is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("startup_runner")

async def setup_folders():
    """Ensure necessary state and upload directories exist."""
    folders = [
        "storage/sessions",
        "storage/state",
        "backend/uploads",
    ]
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            logger.info("Created folder: %s", folder)

def ensure_port_available(host: str, port: int):
    bind_host = host or "0.0.0.0"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((bind_host, port))
    except OSError as exc:
        raise RuntimeError(
            f"Cannot start API on {host}:{port}; port is already in use. "
            "Stop the duplicate backend process/service or set APP_PORT to a free port."
        ) from exc

async def setup_db():
    """Create tables and seed initial data if needed."""
    from backend.database import engine, AsyncSessionLocal
    from backend.models import Base, User, Branch, RatePlan, ServiceType
    from sqlalchemy import select, func

    logger.info("Initializing database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        from backend.migrations import migrate_schema
        await conn.run_sync(migrate_schema)
    logger.info("Database schema initialized.")

    async with AsyncSessionLocal() as session:
        # 1. Seed simulated clients
        user_count_stmt = select(func.count(User.tg_id)).where(User.is_simulated == True)
        user_count_res = await session.execute(user_count_stmt)
        fake_users = user_count_res.scalar() or 0
        
        if fake_users == 0:
            logger.info("No simulated clients found. Seeding 100 fake users...")
            for i in range(1, 101):
                session.add(User(
                    tg_id=1000 + i,
                    full_name=f"Simulated User #{i}",
                    is_simulated=True,
                    lang="uz"
                ))
            await session.commit()
            logger.info("100 fake users seeded successfully.")
        else:
            logger.info("Found %d simulated clients in database.", fake_users)

        # 2. Seed lookup tables from Excel if branches are empty
        branch_count_stmt = select(func.count(Branch.id))
        branch_count_res = await session.execute(branch_count_stmt)
        branches = branch_count_res.scalar() or 0

        if branches == 0:
            logger.info("Lookup tables are empty. Running Excel import seed...")
            try:
                from scripts.seed_from_excel import seed_from_excel
                await seed_from_excel()
                logger.info("Excel seed data imported successfully.")
            except Exception as e:
                logger.error("Failed to seed database from Excel: %s", e, exc_info=True)
        else:
            logger.info("Branches lookup table already seeded.")

        # 3. Seed/Update RatePlans with premium metadata
        logger.info("Seeding/updating rate plans with premium specifications...")
        real_specs = {
            # Mobile
            "Super Salom": {"price": 25000, "minutes": "2000 min", "sms": "1000 SMS", "mb": "5 GB", "description": "Ekonomik muloqot va asosiy internet paketi"},
            "Bonus Super Salom": {"price": 0, "minutes": "1000 min", "sms": "500 SMS", "mb": "2 GB", "description": "Bonus tarif muloqot uchun"},
            "Ideal Plus": {"price": 45000, "minutes": "5000 min", "sms": "2000 SMS", "mb": "15 GB", "description": "Ideal muvozanat: ko'p daqiqalar va barqaror internet"},
            "Bonus Ideal Plus": {"price": 0, "minutes": "2000 min", "sms": "1000 SMS", "mb": "5 GB", "description": "Bonus tarif qo'shimcha imkoniyatlar bilan"},
            "Optimal": {"price": 33000, "minutes": "3000 min", "sms": "1000 SMS", "mb": "10 GB", "description": "Optimal narx va qulay shartlar"},
            "V PLUS": {"price": 50000, "minutes": "4000 min", "sms": "2000 SMS", "mb": "20 GB", "description": "Faol yoshlar uchun katta internet paketi"},
            "Muruvvat": {"price": 15000, "minutes": "1000 min", "sms": "500 SMS", "mb": "3 GB", "description": "Ijtimoiy yordam tarifi"},
            "Mobile Elite": {"price": 120000, "minutes": "Cheksiz", "sms": "10000 SMS", "mb": "Cheksiz", "description": "Premium VIP paket: cheksiz muloqot va internet"},
            "Maktab": {"price": 20000, "minutes": "1500 min", "sms": "500 SMS", "mb": "8 GB", "description": "O'quvchilar va ta'lim uchun maxsus tarif"},
            "Super Lux": {"price": 75000, "minutes": "Cheksiz", "sms": "5000 SMS", "mb": "50 GB", "description": "Yuqori darajadagi foydalanuvchilar uchun"},
            # Internet
            "FOYDALI - 1": {"price": 70000, "speed": "50 Mbps", "description": "Cheksiz yuqori tezlikdagi uy interneti"},
            "FOYDALI - 1+": {"price": 85000, "speed": "70 Mbps", "description": "Cheksiz internet + Wi-Fi router bepul"},
            "FOYDALI - 2+": {"price": 99000, "speed": "100 Mbps", "description": "Tezkor GPON internet + 100 ta IPTV kanallari"},
            "FOYDALI - 3+": {"price": 149000, "speed": "300 Mbps", "description": "Ultra tezkor internet + GPON router + IPTV VIP"},
            "HAMMASI BIRGA 1": {"price": 119000, "speed": "100 Mbps", "description": "Internet 100 Mbps + Mobil aloqa paketi"},
            "HAMMASI BIRGA 1+": {"price": 129000, "speed": "120 Mbps", "description": "Internet 120 Mbps + Mobil daqiqalar va gigabaytlar"},
            "HAMMASI BIRGA 2": {"price": 139000, "speed": "150 Mbps", "description": "Internet 150 Mbps + Mobil VIP paket"},
            "HAMMASI BIRGA 2+": {"price": 169000, "speed": "200 Mbps", "description": "Internet 200 Mbps + Premium TV + Mobil aloqa"},
            "ONLINE PROMO": {"price": 60000, "speed": "40 Mbps", "description": "Maxsus aksiya bo'yicha arzon uy interneti"},
            "UNLIM 7": {"price": 55000, "speed": "30 Mbps", "description": "Barqaror cheksiz uy interneti"}
        }

        for name, specs in real_specs.items():
            # Update if already exists
            stmt = select(RatePlan).where(RatePlan.name == name)
            res = await session.execute(stmt)
            plan = res.scalar_one_or_none()
            if plan:
                plan.price = specs.get("price")
                plan.speed = specs.get("speed")
                plan.minutes = specs.get("minutes")
                plan.sms = specs.get("sms")
                plan.mb = specs.get("mb")
                plan.description = specs.get("description")
                plan.is_active = True
            else:
                # Create if it doesn't exist
                service_type = ServiceType.INTERNET if any(k in name for k in ["FOYDALI", "HAMMASI", "ONLINE", "UNLIM"]) else ServiceType.MOBILE
                new_plan = RatePlan(
                    name=name,
                    service_type=service_type,
                    price=specs.get("price"),
                    speed=specs.get("speed"),
                    minutes=specs.get("minutes"),
                    sms=specs.get("sms"),
                    mb=specs.get("mb"),
                    description=specs.get("description"),
                    is_active=True
                )
                session.add(new_plan)
        
        await session.commit()
        logger.info("Real tariffs seeded/updated successfully.")

async def stream_output(stream, prefix):
    """Utility to stream stdout/stderr of subprocesses to logger."""
    while True:
        line = await stream.readline()
        if not line:
            break
        logger.info("[%s] %s", prefix, line.decode().strip())

async def main():
    # Load settings/config
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)
    import backend.config as settings

    try:
        ensure_port_available(settings.APP_HOST, settings.APP_PORT)
    except RuntimeError as exc:
        logger.error("%s", exc)
        raise SystemExit(1)

    await setup_folders()
    await setup_db()

    # Configure Uvicorn server programmatically
    config = uvicorn.Config(
        app="backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        log_level="info",
        loop="asyncio"
    )
    server = uvicorn.Server(config)

    # Import Telegram support bot entry
    from bot.main import start_bot

    # Import Userbot worker
    from bot.userbot.worker import worker_loop

    # Import Simulation background tasks
    from backend.services.background_tasks import (
        cleanup_loop,
        fake_client_loop,
        fake_client_reply_loop,
    )


    # Compile running tasks
    tasks = [
        asyncio.create_task(server.serve()),
        asyncio.create_task(start_bot()),
        asyncio.create_task(cleanup_loop()),
    ]

    if settings.FAKE_ENABLED:
        logger.info("Simulation engine and Auto-Operator worker are enabled.")
        tasks.append(asyncio.create_task(worker_loop()))
        tasks.append(asyncio.create_task(fake_client_loop()))
        tasks.append(asyncio.create_task(fake_client_reply_loop()))
    else:
        logger.info("Simulation engine is disabled.")

    logger.info("All processes are active and running.")
    try:
        await asyncio.gather(*tasks)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutdown requested.")
    finally:
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process stopped.")
