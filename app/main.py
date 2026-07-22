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
from app.services import AnimeTraceClient, HybridSearchService, SauceNaoClient, TraceMoeClient


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="help", description="Как пользоваться"),
            BotCommand(command="privacy", description="Конфиденциальность"),
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
    dp = Dispatcher()
    dp.include_router(router)

    timeout = aiohttp.ClientTimeout(total=settings.request_timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        trace_client = TraceMoeClient(
            session=session,
            api_key=settings.trace_moe_api_key,
        )
        anime_trace_client = AnimeTraceClient(
            session=session,
            api_url=settings.anime_trace_api_url,
            api_key=settings.anime_trace_api_key,
            model=settings.anime_trace_model,
        )
        saucenao_client = SauceNaoClient(
            session=session,
            api_key=settings.saucenao_api_key,
            num_results=settings.saucenao_num_results,
        )

        search_service = HybridSearchService(
            settings=settings,
            trace_client=trace_client,
            anime_trace_client=anime_trace_client,
            saucenao_client=saucenao_client,
        )

        try:
            await bot.delete_webhook(
                drop_pending_updates=settings.drop_pending_updates
            )
            await set_commands(bot)
            await dp.start_polling(
                bot,
                settings=settings,
                search_service=search_service,
                allowed_updates=dp.resolve_used_update_types(),
            )
        finally:
            await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Бот остановлен.")
