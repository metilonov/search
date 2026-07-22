from __future__ import annotations

import asyncio
import logging
import sys

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.config import Settings
from app.handlers import router
from app.services import TraceMoeClient


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="help", description="Как искать аниме"),
            BotCommand(
                command="privacy",
                description="Конфиденциальность",
            ),
        ]
    )


async def main() -> None:
    settings = Settings.from_env()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True,
        ),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    timeout = aiohttp.ClientTimeout(total=settings.request_timeout)
    async with aiohttp.ClientSession(timeout=timeout) as http_session:
        trace_client = TraceMoeClient(
            session=http_session,
            api_key=settings.trace_moe_api_key,
        )

        try:
            await bot.delete_webhook(
                drop_pending_updates=settings.drop_pending_updates
            )
            await set_commands(bot)
            await dispatcher.start_polling(
                bot,
                trace_client=trace_client,
                settings=settings,
                allowed_updates=dispatcher.resolve_used_update_types(),
            )
        finally:
            await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Бот остановлен.")
