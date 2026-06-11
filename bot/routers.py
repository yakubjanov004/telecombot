from aiogram import Router

from bot.handlers.auth import router as auth_router
from bot.handlers.role_menus import router as role_menus_router
from bot.handlers.operator.topic_relay import router as topic_relay_router


def get_main_router() -> Router:
    main_router = Router()
    
    # Order of inclusion is important for resolving filters
    main_router.include_router(auth_router)
    main_router.include_router(role_menus_router)
    main_router.include_router(topic_relay_router)
    
    return main_router
