from __future__ import annotations

import html
from typing import Any

from app.models import TraceMatch


def format_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_episode(value: Any) -> str:
    if value is None:
        return "не определён"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "не определён"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def build_result_caption(
    match: TraceMatch,
    position: int,
    low_confidence: bool = False,
) -> str:
    primary = html.escape(match.titles.primary())
    alternatives = [
        html.escape(title) for title in match.titles.alternatives()[:2]
    ]

    lines = [
        f"<b>Результат №{position}</b>",
        "",
        f"🎞 <b>Аниме:</b> {primary}",
    ]

    if alternatives:
        lines.append(f"🔤 <b>Другие названия:</b> {' / '.join(alternatives)}")

    lines.extend(
        [
            f"📺 <b>Эпизод:</b> {html.escape(format_episode(match.episode))}",
            (
                "⏱ <b>Таймкод:</b> "
                f"{format_timestamp(match.time_from)}–"
                f"{format_timestamp(match.time_to)}"
            ),
            f"🎯 <b>Сходство:</b> {match.similarity * 100:.2f}%",
        ]
    )

    if match.is_adult:
        lines.append("🔞 <b>Категория:</b> контент для взрослых")

    if low_confidence:
        lines.extend(
            [
                "",
                "⚠️ Совпадение слабое. Попробуйте отправить кадр без "
                "субтитров, рамок и интерфейса видеоплеера.",
            ]
        )

    return "\n".join(lines)
