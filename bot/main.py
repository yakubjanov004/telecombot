import asyncio
import logging
from bot.core.loader import bot, dp
from bot.routers import get_main_router
from bot.middlewares.db_session import DbSessionMiddleware

logger = logging.getLogger(__name__)


async def start_bot():
    logger.info("Initializing Telegram bot routers and middlewares...")
    dp.include_router(get_main_router())
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    
    logger.info("Starting Telegram bot long polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Telegram bot error: {e}", exc_info=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    asyncio.run(start_bot())
