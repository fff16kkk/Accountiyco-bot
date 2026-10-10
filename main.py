import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import user_router, admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    if not BOT_TOKEN or BOT_TOKEN == "TOKEN_HERE":
        logger.error("❌ لطفاً توکن ربات را در فایل config.py یا .env قرار دهید!")
        return

    # ساخت دیتابیس
    await init_db()
    logger.info("✅ دیتابیس آماده شد.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # ثبت روترها
    dp.include_router(admin_router)
    dp.include_router(user_router)

    logger.info("🤖 ربات در حال اجرا...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
