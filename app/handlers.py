from __future__ import annotations

import asyncio
import logging
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.config import Settings
from app.keyboards import hit_keyboard
from app.models import SearchHit
from app.services import HybridSearchService, build_variants
from app.utils import format_hit_caption

logger = logging.getLogger(__name__)
router = Router(name="hybrid-anime-search")

_active_users: set[int] = set()
_lock = asyncio.Lock()


async def _claim(user_id: int) -> bool:
    async with _lock:
        if user_id in _active_users:
            return False
        _active_users.add(user_id)
        return True


async def _release(user_id: int) -> None:
    async with _lock:
        _active_users.discard(user_id)


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "<b>🔎 Гибридный поиск аниме по фото</b>\n\n"
        "Я использую 3 движка:\n"
        "1. trace.moe — ищет точный кадр, эпизод и таймкод\n"
        "2. AnimeTrace — ищет персонажа и название\n"
        "3. SauceNAO — ищет арты, источники и похожие материалы\n\n"
        "Просто отправьте скриншот или изображение файлом."
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(
        "<b>Как использовать</b>\n\n"
        "• Отправьте кадр из аниме как фото или документ.\n"
        "• Для лучшего результата обрежьте чёрные рамки и интерфейс плеера.\n"
        "• Бот умеет автоматически пробовать несколько вариантов кадра.\n\n"
        "<b>Идеальная схема:</b> trace.moe → AnimeTrace → SauceNAO."
    )


@router.message(Command("privacy"))
async def privacy_handler(message: Message) -> None:
    await message.answer(
        "Изображение отправляется во внешние сервисы поиска только "
        "для распознавания. Не отправляйте личные фотографии и документы."
    )


@router.message(F.photo)
async def photo_handler(
    message: Message,
    bot: Bot,
    search_service: HybridSearchService,
    settings: Settings,
) -> None:
    photo = message.photo[-1]
    await _process_image(
        message=message,
        bot=bot,
        search_service=search_service,
        settings=settings,
        file_id=photo.file_id,
        file_size=photo.file_size,
        filename="telegram_photo.jpg",
        content_type="image/jpeg",
    )


@router.message(F.document)
async def document_handler(
    message: Message,
    bot: Bot,
    search_service: HybridSearchService,
    settings: Settings,
) -> None:
    document = message.document
    mime = (document.mime_type or "").lower()
    if not mime.startswith("image/"):
        await message.answer("❌ Это не изображение. Отправьте JPG, PNG или WEBP.")
        return

    await _process_image(
        message=message,
        bot=bot,
        search_service=search_service,
        settings=settings,
        file_id=document.file_id,
        file_size=document.file_size,
        filename=document.file_name or "image",
        content_type=mime,
    )


async def _process_image(
    *,
    message: Message,
    bot: Bot,
    search_service: HybridSearchService,
    settings: Settings,
    file_id: str,
    file_size: int | None,
    filename: str,
    content_type: str,
) -> None:
    user_id = message.from_user.id if message.from_user else message.chat.id
    max_bytes = settings.max_image_size_mb * 1024 * 1024

    if file_size and file_size > max_bytes:
        await message.answer(
            f"❌ Файл слишком большой. Максимум: {settings.max_image_size_mb} МБ."
        )
        return

    if not await _claim(user_id):
        await message.answer("⏳ Подождите, предыдущее изображение ещё обрабатывается.")
        return

    status = await message.answer("🔎 Запускаю гибридный поиск аниме…")

    try:
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        downloaded = await bot.download(file_id)
        if downloaded is None:
            raise RuntimeError("Не удалось скачать файл из Telegram.")

        if isinstance(downloaded, BytesIO):
            image_bytes = downloaded.getvalue()
        else:
            downloaded.seek(0)
            image_bytes = downloaded.read()

        if len(image_bytes) > max_bytes:
            await status.edit_text(
                f"❌ Файл слишком большой. Максимум: {settings.max_image_size_mb} МБ."
            )
            return

        variants = build_variants(
            image_bytes=image_bytes,
            filename=filename,
            content_type=content_type,
            enabled=settings.use_auto_variants,
        )

        report = await search_service.search(variants)

        try:
            await status.edit_text(report.summary or "Поиск завершён.")
        except TelegramBadRequest:
            pass

        hits = report.all_hits()
        if not hits:
            await message.answer(
                "😕 Ничего не найдено. Попробуйте другой кадр без субтитров и рамок."
            )
            return

        number = 1
        for group_name, group_hits in (
            ("trace.moe", report.trace_hits),
            ("AnimeTrace", report.anime_trace_hits),
            ("SauceNAO", report.saucenao_hits),
        ):
            if not group_hits:
                continue

            if len(hits) > 1:
                await message.answer(f"<b>{group_name}</b>")

            for hit in group_hits:
                await _send_hit(message, hit, number)
                number += 1

        if report.low_confidence:
            await message.answer(
                "⚠️ Уверенного совпадения по кадру не было. "
                "Показаны лучшие результаты из нескольких движков."
            )

    except Exception:
        logger.exception("Ошибка при гибридном поиске аниме")
        try:
            await status.edit_text("❌ Произошла внутренняя ошибка. Проверьте логи.")
        except TelegramBadRequest:
            pass
    finally:
        await _release(user_id)


async def _send_hit(message: Message, hit: SearchHit, number: int) -> None:
    caption = format_hit_caption(hit, number)
    keyboard = hit_keyboard(hit)

    if hit.preview_image:
        try:
            await message.answer_photo(
                photo=hit.preview_image,
                caption=caption,
                reply_markup=keyboard,
            )
            return
        except (TelegramBadRequest, TelegramNetworkError):
            logger.warning("Не удалось отправить превью результата", exc_info=True)

    await message.answer(caption, reply_markup=keyboard)


@router.message()
async def fallback_handler(message: Message) -> None:
    await message.answer(
        "Отправьте изображение аниме-кадра. "
        "Команда /help покажет инструкцию."
    )
