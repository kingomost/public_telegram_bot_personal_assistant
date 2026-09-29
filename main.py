import asyncio
import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from aiogram import Bot
from aiogram import Dispatcher
from aiogram.utils.token import TokenValidationError, validate_token

import config
from middlewares.auth_middleware import AuthMiddleware
from middlewares.activity_middleware import ActivityMiddleware
# from routers import router as router_endpoints
from endpoints import router as endpoints
from services.heartbeat import tick


def validate_config() -> None:
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not configured")
    try:
        validate_token(config.BOT_TOKEN)
    except TokenValidationError as error:
        raise RuntimeError("BOT_TOKEN has an invalid format") from error
    if not isinstance(config.OWNER_ID, int) or config.OWNER_ID <= 0:
        raise RuntimeError("OWNER_ID must be a positive integer")
    if config.BOT_TICK_INTERVAL_SEC <= 0:
        raise RuntimeError("BOT_TICK_INTERVAL_SEC must be positive")
    try:
        ZoneInfo(config.TIME_ZONE)
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise RuntimeError(f"Unknown TIME_ZONE: {config.TIME_ZONE}") from error

async def main():
    validate_config()
    dp = Dispatcher()
    dp.include_router(endpoints)
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.message.middleware(ActivityMiddleware())
    dp.callback_query.middleware(ActivityMiddleware())

    logging.basicConfig(level = logging.INFO)
    bot = Bot(token=config.BOT_TOKEN)

    interval = config.BOT_TICK_INTERVAL_SEC
    kwargs = { "bot": bot }
    scheduler = AsyncIOScheduler()
    scheduler.add_job(tick, trigger = "interval", seconds = interval, kwargs = kwargs)
    scheduler.start()

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
