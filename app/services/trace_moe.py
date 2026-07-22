from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from app.models import TraceMatch


class TraceMoeError(RuntimeError):
    """Base trace.moe API error."""


class TraceMoeBadImageError(TraceMoeError):
    """The API could not process the supplied image."""


class TraceMoeRateLimitError(TraceMoeError):
    """The API quota or request limit was exceeded."""


class TraceMoeTemporaryError(TraceMoeError):
    """Temporary trace.moe service failure."""


class TraceMoeClient:
    SEARCH_URL = (
        "https://api.trace.moe/search?anilistInfo&cutBorders"
    )

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str | None = None,
        concurrency: int = 2,
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._semaphore = asyncio.Semaphore(concurrency)

    async def search(
        self,
        image: bytes,
        filename: str = "image.jpg",
        content_type: str = "image/jpeg",
    ) -> list[TraceMatch]:
        if not image:
            raise TraceMoeBadImageError("Получен пустой файл.")

        form = aiohttp.FormData()
        form.add_field(
            "image",
            image,
            filename=filename,
            content_type=content_type,
        )

        headers = {
            "Accept": "application/json",
            "User-Agent": "AnimePhotoTelegramBot/1.0",
        }
        if self._api_key:
            headers["x-trace-key"] = self._api_key

        try:
            async with self._semaphore:
                async with self._session.post(
                    self.SEARCH_URL,
                    data=form,
                    headers=headers,
                ) as response:
                    payload = await self._read_json(response)
                    self._raise_for_status(response.status, payload)
        except asyncio.TimeoutError as exc:
            raise TraceMoeTemporaryError(
                "Сервис не ответил вовремя."
            ) from exc
        except aiohttp.ClientError as exc:
            raise TraceMoeTemporaryError(
                "Не удалось подключиться к trace.moe."
            ) from exc

        raw_results = payload.get("result")
        if not isinstance(raw_results, list):
            raise TraceMoeTemporaryError(
                "Сервис вернул ответ неизвестного формата."
            )

        matches: list[TraceMatch] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            try:
                matches.append(TraceMatch.from_api(item))
            except (TypeError, ValueError):
                continue

        matches.sort(key=lambda item: item.similarity, reverse=True)
        return matches

    @staticmethod
    async def _read_json(
        response: aiohttp.ClientResponse,
    ) -> dict[str, Any]:
        try:
            payload = await response.json(content_type=None)
        except (aiohttp.ContentTypeError, ValueError) as exc:
            body = (await response.text())[:300]
            raise TraceMoeTemporaryError(
                f"Некорректный ответ сервиса: {body}"
            ) from exc

        if not isinstance(payload, dict):
            raise TraceMoeTemporaryError(
                "Сервис вернул не JSON-объект."
            )
        return payload

    @staticmethod
    def _raise_for_status(
        status: int,
        payload: dict[str, Any],
    ) -> None:
        if status == 200:
            api_error = payload.get("error")
            if api_error:
                raise TraceMoeError(str(api_error))
            return

        error_text = str(payload.get("error") or "Неизвестная ошибка")

        if status == 400:
            raise TraceMoeBadImageError(error_text)
        if status in {402, 429}:
            raise TraceMoeRateLimitError(error_text)
        if status in {500, 502, 503, 504}:
            raise TraceMoeTemporaryError(error_text)
        raise TraceMoeError(f"trace.moe HTTP {status}: {error_text}")
