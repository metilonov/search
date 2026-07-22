from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models import SearchHit


def hit_keyboard(hit: SearchHit) -> InlineKeyboardMarkup | None:
    rows: list[list[InlineKeyboardButton]] = []

    if hit.links:
        row: list[InlineKeyboardButton] = []
        for text, url in hit.links[:3]:
            row.append(InlineKeyboardButton(text=text, url=url))
        if row:
            rows.append(row)

    extra: list[InlineKeyboardButton] = []
    if hit.preview_video:
        extra.append(
            InlineKeyboardButton(text="🎬 Превью", url=hit.preview_video)
        )
    if extra:
        rows.append(extra)

    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)
