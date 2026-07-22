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
from app.keyboards import result_keyboard
from app.services import (
    TraceMoeBadImageError,
    TraceMoeClient,
    TraceMoeError,
    TraceMoeRateLimitError,
    TraceMoeTemporaryError,
)
from app.utils import build_result_caption

logger = logging.getLogger(__name__)
router = Router(name="anime-photo-search")

_active_users: set[int] = set()
_active_users_lock = asyncio.Lock()


async def _claim_user(user_id: int) -> bool:
    async with _active_users_lock:
        if user_id in _active_users:
            return False
        _active_users.add(user_id)
        return True


async def _release_user(user_id: int) -> None:
    async with _active_users_lock:
        _active_users.discard(user_id)


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "<b>🔎 Поиск аниме по кадру</b>\n\n"
        "Отправьте мне скриншот или изображение файлом. "
        "Я попробую определить:\n"
        "• название аниме;\n"
        "• эпизод;\n"
        "• примерный таймкод;\n"
        "• процент сходства.\n\n"
        "<b>Совет:</b> лучше всего работают чистые кадры без "
        "субтитров, рамок и кнопок видеоплеера."
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(
        "<b>Как пользоваться ботом</b>\n\n"
        "1. Сделайте скриншот сцены из аниме.\n"
        "2. Отправьте его как фото или как файл.\n"
        "3. Подождите результат поиска.\n\n"
        "Поддерживаются изображения размером до 20 МБ. "
        "Для лучшей точности кадрируйте чёрные поля и интерфейс."
    )


@router.message(Command("privacy"))
async def privacy_handler(message: Message) -> None:
    await message.answer(
        "<b>Конфиденциальность</b>\n\n"
        "Изображение загружается в trace.moe только для поиска "
        "совпадения. Не отправляйте личные фотографии или документы."
    )


@router.message(F.photo)
async def photo_handler(
    message: Message,
    bot: Bot,
    trace_client: TraceMoeClient,
    settings: Settings,
) -> None:
    photo = message.photo[-1]
    await _process_image(
        message=message,
        bot=bot,
        trace_client=trace_client,
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
    trace_client: TraceMoeClient,
    settings: Settings,
) -> None:
    document = message.document
    mime_type = (document.mime_type or "").lower()

    if not mime_type.startswith("image/"):
        await message.answer(
            "❌ Это не изображение. Отправьте JPG, PNG или WEBP."
        )
        return

    await _process_image(
        message=message,
        bot=bot,
        trace_client=trace_client,
        settings=settings,
        file_id=document.file_id,
        file_size=document.file_size,
        filename=document.file_name or "telegram_image",
        content_type=mime_type,
    )


async def _process_image(
    *,
    message: Message,
    bot: Bot,
    trace_client: TraceMoeClient,
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
            f"❌ Файл слишком большой. Максимум: "
            f"{settings.max_image_size_mb} МБ."
        )
        return

    if not await _claim_user(user_id):
        await message.answer(
            "⏳ Я уже обрабатываю ваше предыдущее изображение."
        )
        return

    status_message = await message.answer("🔎 Ищу аниме по кадру…")

    try:
        await bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING,
        )

        downloaded = await bot.download(file_id)
        if downloaded is None:
            raise RuntimeError("Telegram не вернул содержимое файла.")

        if isinstance(downloaded, BytesIO):
            image_bytes = downloaded.getvalue()
        else:
            downloaded.seek(0)
            image_bytes = downloaded.read()

        if len(image_bytes) > max_bytes:
            await status_message.edit_text(
                f"❌ Файл слишком большой. Максимум: "
                f"{settings.max_image_size_mb} МБ."
            )
            return

        matches = await trace_client.search(
            image=image_bytes,
            filename=filename,
            content_type=content_type,
        )

        if not matches:
            await status_message.edit_text(
                "😕 Совпадений не найдено. Попробуйте другой кадр."
            )
            return

        confident = [
            match
            for match in matches
            if match.similarity >= settings.min_similarity
        ]
        low_confidence = not confident
        selected = (
            confident[: settings.max_results]
            if confident
            else matches[:1]
        )

        try:
            await status_message.delete()
        except TelegramBadRequest:
            pass

        for position, match in enumerate(selected, start=1):
            caption = build_result_caption(
                match=match,
                position=position,
                low_confidence=low_confidence,
            )
            keyboard = result_keyboard(match)

            if match.preview_image:
                try:
                    await message.answer_photo(
                        photo=match.preview_image,
                        caption=caption,
                        reply_markup=keyboard,
                    )
                    continue
                except (TelegramBadRequest, TelegramNetworkError):
                    logger.warning(
                        "Не удалось отправить превью trace.moe",
                        exc_info=True,
                    )

            await message.answer(
                caption,
                reply_markup=keyboard,
            )

    except TraceMoeBadImageError:
        await status_message.edit_text(
            "❌ trace.moe не смог обработать изображение. "
            "Попробуйте отправить JPG или PNG."
        )
    except TraceMoeRateLimitError:
        await status_message.edit_text(
            "⏳ Лимит trace.moe временно исчерпан. "
            "Попробуйте немного позже."
        )
    except TraceMoeTemporaryError:
        logger.warning("Временная ошибка trace.moe", exc_info=True)
        await status_message.edit_text(
            "⚠️ trace.moe временно недоступен. "
            "Попробуйте повторить поиск позже."
        )
    except TraceMoeError as exc:
        logger.warning("Ошибка trace.moe: %s", exc)
        await status_message.edit_text(
            "❌ Сервис поиска вернул ошибку."
        )
    except Exception:
        logger.exception("Необработанная ошибка при поиске аниме")
        try:
            await status_message.edit_text(
                "❌ Произошла внутренняя ошибка. "
                "Проверьте журнал приложения."
            )
        except TelegramBadRequest:
            pass
    finally:
        await _release_user(user_id)


@router.message()
async def fallback_handler(message: Message) -> None:
    await message.answer(
        "Отправьте изображение сцены из аниме. "
        "Команда /help покажет инструкцию."
    )
