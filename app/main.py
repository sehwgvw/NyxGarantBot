import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.bot.handlers import admin, deals, group_commands, menu, start, support
from app.config import get_settings
from app.db.session import SessionLocal, init_db
from app.services.backups import run_pg_backup


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    await init_db()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(deals.router)
    dp.include_router(menu.router)
    dp.include_router(support.router)
    dp.include_router(group_commands.router)
    dp.include_router(admin.router)

    scheduler = AsyncIOScheduler(timezone="UTC")
    if settings.backup_enabled:
        async def backup_job() -> None:
            async with SessionLocal() as session:
                await run_pg_backup(settings, session)

        scheduler.add_job(backup_job, "interval", hours=settings.backup_interval_hours, id="db_backup", replace_existing=True)
    scheduler.start()

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
