from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} должен быть числом.") from exc


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} должен быть целым числом.") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    trace_moe_api_key: str | None
    min_similarity: float
    max_results: int
    request_timeout: float
    max_image_size_mb: int
    drop_pending_updates: bool

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError(
                "Не задан BOT_TOKEN. Скопируйте .env.example в .env "
                "и вставьте токен от @BotFather."
            )

        min_similarity = _get_float("MIN_SIMILARITY", 0.65)
        if not 0 <= min_similarity <= 1:
            raise RuntimeError("MIN_SIMILARITY должен быть от 0 до 1.")

        max_results = _get_int("MAX_RESULTS", 3)
        if not 1 <= max_results <= 5:
            raise RuntimeError("MAX_RESULTS должен быть от 1 до 5.")

        max_image_size_mb = _get_int("MAX_IMAGE_SIZE_MB", 20)
        if not 1 <= max_image_size_mb <= 20:
            raise RuntimeError("MAX_IMAGE_SIZE_MB должен быть от 1 до 20.")

        api_key = os.getenv("TRACE_MOE_API_KEY", "").strip() or None

        return cls(
            bot_token=token,
            trace_moe_api_key=api_key,
            min_similarity=min_similarity,
            max_results=max_results,
            request_timeout=_get_float("REQUEST_TIMEOUT", 35.0),
            max_image_size_mb=max_image_size_mb,
            drop_pending_updates=_get_bool("DROP_PENDING_UPDATES", False),
        )
