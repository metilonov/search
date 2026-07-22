from __future__ import annotations

import html

from app.models import SearchHit


def clamp_similarity(value: float | None) -> str:
    if value is None:
        return "не указано"
    return f"{value * 100:.2f}%"


def seconds_to_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_hit_caption(hit: SearchHit, number: int) -> str:
    lines = [
        f"<b>Результат №{number}</b>",
        "",
        f"🧠 <b>Источник:</b> {html.escape(hit.engine)}",
        f"🎞 <b>Название:</b> {html.escape(hit.title)}",
    ]

    if hit.subtitle:
        lines.append(f"👤 <b>Дополнительно:</b> {html.escape(hit.subtitle)}")
    if hit.episode:
        lines.append(f"📺 <b>Эпизод:</b> {html.escape(hit.episode)}")
    if hit.timestamp:
        lines.append(f"⏱ <b>Таймкод:</b> {html.escape(hit.timestamp)}")
    if hit.similarity is not None:
        lines.append(f"🎯 <b>Сходство:</b> {clamp_similarity(hit.similarity)}")
    if hit.variant and hit.variant != "original":
        lines.append(f"🖼 <b>Вариант кадра:</b> {html.escape(hit.variant)}")
    if hit.note:
        lines.append(f"ℹ️ <b>Примечание:</b> {html.escape(hit.note)}")

    return "\n".join(lines)
