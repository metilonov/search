from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models import TraceMatch


def result_keyboard(match: TraceMatch) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if match.anilist_id:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📚 Открыть в AniList",
                    url=f"https://anilist.co/anime/{match.anilist_id}",
                )
            ]
        )

    secondary: list[InlineKeyboardButton] = []
    if match.preview_video:
        secondary.append(
            InlineKeyboardButton(
                text="🎬 Превью сцены",
                url=match.preview_video,
            )
        )
    if match.mal_id:
        secondary.append(
            InlineKeyboardButton(
                text="MyAnimeList",
                url=f"https://myanimelist.net/anime/{match.mal_id}",
            )
        )
    if secondary:
        rows.append(secondary)

    return InlineKeyboardMarkup(inline_keyboard=rows)
