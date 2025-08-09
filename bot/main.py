import asyncio
import logging
import os

from logging.config import dictConfig
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from db.engine import async_session_factory
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from bot.config import settings
from bot.handlers import common, profile, search
from db.repository import UserRepo, CacheRepo
from bot.services import UserService, SearchService, run_scrapers_and_update_cache
from bot.logging_config import LOGGING_CONFIG
from aiogram.types import BotCommand, BotCommandScopeDefault

if not os.path.exists("logs"):
    os.makedirs("logs")
dictConfig(LOGGING_CONFIG)


class DIMiddleware:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __call__(self, handler, event, data):
        async with self.session_factory() as session:
            data["user_repo"] = UserRepo(session)
            data["cache_repo"] = CacheRepo(session)
            data["user_service"] = UserService(data["user_repo"])
            data["search_service"] = SearchService(data["cache_repo"])
            return await handler(event, data)


async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command="/start", description="🚀 Перезапустить бота"),
        BotCommand(command="/check", description="🔍 Начать новую проверку"),
        BotCommand(command="/profile", description="👤 Мой профиль и подписка"),
    ]

    # Устанавливаем команды для всех пользователей
    await bot.set_my_commands(main_menu_commands, BotCommandScopeDefault())


async def main():
    bot = Bot(token=settings.BOT_TOKEN)

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.update.middleware(DIMiddleware(async_session_factory))

    dp.include_router(common.router)
    dp.include_router(profile.router)
    dp.include_router(search.router)

    jobstores = {
        "default": SQLAlchemyJobStore(
            url=settings.DATABASE_URL_pymysql,
        )
    }

    scheduler = AsyncIOScheduler(jobstores=jobstores)
    scheduler.add_job(
        run_scrapers_and_update_cache,
        "interval",
        hours=6,
        id="update_cache_job",
        replace_existing=True,
    )
    await set_main_menu(bot)
    logging.info("Starting initial data scraping...")
    await run_scrapers_and_update_cache()
    logging.info("Initial scraping finished.")
    scheduler.start()

    logging.info("Starting bot polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
