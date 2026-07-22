from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} должен быть целым числом.") from exc


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} должен быть числом.") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    request_timeout: float
    max_image_size_mb: int
    drop_pending_updates: bool

    trace_moe_api_key: str | None
    trace_confident_score: float
    trace_min_score: float
    trace_max_results: int

    anime_trace_enabled: bool
    anime_trace_api_url: str
    anime_trace_api_key: str | None
    anime_trace_model: str | None
    anime_trace_min_score: float

    saucenao_enabled: bool
    saucenao_api_key: str | None
    saucenao_min_score: float
    saucenao_num_results: int

    use_auto_variants: bool

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError(
                "Не задан BOT_TOKEN. Скопируйте .env.example в .env "
                "и вставьте токен от @BotFather."
            )

        trace_confident_score = _get_float("TRACE_CONFIDENT_SCORE", 0.80)
        trace_min_score = _get_float("TRACE_MIN_SCORE", 0.65)
        anime_trace_min_score = _get_float("ANIME_TRACE_MIN_SCORE", 0.55)
        saucenao_min_score = _get_float("SAUCENAO_MIN_SCORE", 0.60)

        for name, value in (
            ("TRACE_CONFIDENT_SCORE", trace_confident_score),
            ("TRACE_MIN_SCORE", trace_min_score),
            ("ANIME_TRACE_MIN_SCORE", anime_trace_min_score),
            ("SAUCENAO_MIN_SCORE", saucenao_min_score),
        ):
            if not 0 <= value <= 1:
                raise RuntimeError(f"{name} должен быть в диапазоне от 0 до 1.")

        return cls(
            bot_token=token,
            request_timeout=_get_float("REQUEST_TIMEOUT", 40.0),
            max_image_size_mb=_get_int("MAX_IMAGE_SIZE_MB", 20),
            drop_pending_updates=_get_bool("DROP_PENDING_UPDATES", False),
            trace_moe_api_key=os.getenv("TRACE_MOE_API_KEY", "").strip() or None,
            trace_confident_score=trace_confident_score,
            trace_min_score=trace_min_score,
            trace_max_results=_get_int("TRACE_MAX_RESULTS", 3),
            anime_trace_enabled=_get_bool("ANIME_TRACE_ENABLED", True),
            anime_trace_api_url=os.getenv(
                "ANIME_TRACE_API_URL",
                "https://api.animedb.cn/v1/search",
            ).strip(),
            anime_trace_api_key=os.getenv("ANIME_TRACE_API_KEY", "").strip() or None,
            anime_trace_model=os.getenv("ANIME_TRACE_MODEL", "").strip() or None,
            anime_trace_min_score=anime_trace_min_score,
            saucenao_enabled=_get_bool("SAUCENAO_ENABLED", True),
            saucenao_api_key=os.getenv("SAUCENAO_API_KEY", "").strip() or None,
            saucenao_min_score=saucenao_min_score,
            saucenao_num_results=_get_int("SAUCENAO_NUM_RESULTS", 3),
            use_auto_variants=_get_bool("USE_AUTO_VARIANTS", True),
        )
