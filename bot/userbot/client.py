import logging
import backend.config as settings

logger = logging.getLogger(__name__)

userbot_app = None
userbot_id = None


def get_cached_userbot_id():
    """Return the cached userbot ID without starting Pyrogram."""
    return userbot_id


async def _reset_userbot():
    global userbot_app, userbot_id

    app = userbot_app
    userbot_app = None
    userbot_id = None

    if app and getattr(app, "is_connected", False):
        try:
            await app.stop()
        except Exception as stop_err:
            logger.debug("Failed to stop invalid userbot session: %s", stop_err)


async def get_userbot():
    """
    Returns the userbot client. If credentials aren't provided, returns None.
    Caches the userbot's own user ID for filtering purposes.
    """
    global userbot_app, userbot_id

    if not settings.FAKE_ENABLED:
        return None
    
    if userbot_app is None:
        if settings.USERBOT_API_ID and settings.USERBOT_API_HASH:
            from pyrogram import Client
            userbot_app = Client(
                name=settings.USERBOT_SESSION_NAME,
                api_id=settings.USERBOT_API_ID,
                api_hash=settings.USERBOT_API_HASH,
                phone_number=settings.USERBOT_PHONE,
            )
            logger.info("Userbot client initialized.")
        else:
            logger.warning("Userbot credentials not found in config.")
            return None

    if not userbot_app.is_connected:
        try:
            await userbot_app.start()
            logger.info("Userbot client started.")

            try:
                async for _ in userbot_app.get_dialogs(limit=100):
                    pass
                logger.info("Dialogs cached successfully.")
            except Exception as cache_err:
                logger.warning(f"Could not cache dialogs: {cache_err}")

        except Exception as e:
            logger.error(f"Failed to start userbot: {e}")
            await _reset_userbot()
            return None

    if userbot_id is None:
        try:
            me = await userbot_app.get_me()
            userbot_id = me.id
            logger.info(f"Cached Userbot ID: {userbot_id}")
        except Exception as e:
            logger.error(f"Failed to resolve userbot identity: {e}")
            await _reset_userbot()
            return None

    return userbot_app


async def get_userbot_id():
    """
    Helper to get the userbot's user ID without needing the full app object.
    """
    app = await get_userbot()
    if app:
        return userbot_id
    return None
