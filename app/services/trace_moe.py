from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from app.models import SearchHit
from app.services.types import SearchServiceError, TemporaryServiceError
from app.utils import seconds_to_timestamp


class TraceMoeClient:
    SEARCH_URL = "https://api.trace.moe/search?anilistInfo&cutBorders"

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str | None = None,
    ) -> None:
        self._session = session
        self._api_key = api_key

    async def search(
        self,
        image: bytes,
        filename: str,
        content_type: str,
        variant_name: str = "original",
        limit: int = 3,
    ) -> list[SearchHit]:
        form = aiohttp.FormData()
        form.add_field(
            "image",
            image,
            filename=filename,
            content_type=content_type,
        )

        headers = {
            "Accept": "application/json",
            "User-Agent": "AnimeHybridBot/2.0",
        }
        if self._api_key:
            headers["x-trace-key"] = self._api_key

        try:
            async with self._session.post(
                self.SEARCH_URL,
                data=form,
                headers=headers,
            ) as response:
                payload = await self._read_json(response)
        except asyncio.TimeoutError as exc:
            raise TemporaryServiceError("trace.moe не ответил вовремя.") from exc
        except aiohttp.ClientError as exc:
            raise TemporaryServiceError("Ошибка подключения к trace.moe.") from exc

        if response.status in {402, 429}:
            raise SearchServiceError("trace.moe временно ограничил запросы.")
        if response.status >= 500:
            raise TemporaryServiceError("trace.moe временно недоступен.")
        if response.status >= 400:
            raise SearchServiceError(str(payload.get("error") or "Ошибка trace.moe."))

        raw_results = payload.get("result") or []
        hits: list[SearchHit] = []

        for item in raw_results[:limit]:
            if not isinstance(item, dict):
                continue

            anilist = item.get("anilist") or {}
            if isinstance(anilist, dict):
                title_data = anilist.get("title") or {}
                title = (
                    title_data.get("english")
                    or title_data.get("romaji")
                    or title_data.get("native")
                    or "Название не найдено"
                )
                alt_parts = [
                    value
                    for value in (
                        title_data.get("romaji"),
                        title_data.get("native"),
                    )
                    if value and value != title
                ]
                subtitle = " / ".join(alt_parts) if alt_parts else None
                anilist_id = anilist.get("id")
                mal_id = anilist.get("idMal")
            else:
                title = "Название не найдено"
                subtitle = None
                anilist_id = None
                mal_id = None

            episode = item.get("episode")
            if episode is not None:
                episode = str(int(episode)) if isinstance(episode, float) and episode.is_integer() else str(episode)

            time_from = float(item.get("from") or 0)
            time_to = float(item.get("to") or 0)
            timestamp = f"{seconds_to_timestamp(time_from)}–{seconds_to_timestamp(time_to)}"

            links: list[tuple[str, str]] = []
            if anilist_id:
                links.append(("AniList", f"https://anilist.co/anime/{anilist_id}"))
            if mal_id:
                links.append(("MyAnimeList", f"https://myanimelist.net/anime/{mal_id}"))

            hits.append(
                SearchHit(
                    engine="trace.moe",
                    title=str(title),
                    similarity=float(item.get("similarity") or 0),
                    subtitle=subtitle,
                    episode=episode,
                    timestamp=timestamp,
                    preview_image=str(item.get("image") or "") or None,
                    preview_video=str(item.get("video") or "") or None,
                    links=tuple(links),
                    variant=variant_name,
                )
            )

        return hits

    @staticmethod
    async def _read_json(response: aiohttp.ClientResponse) -> dict[str, Any]:
        try:
            payload = await response.json(content_type=None)
        except Exception as exc:
            body = (await response.text())[:300]
            raise TemporaryServiceError(f"Некорректный ответ trace.moe: {body}") from exc

        if not isinstance(payload, dict):
            raise TemporaryServiceError("trace.moe вернул неизвестный формат.")
        return payload
