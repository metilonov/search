from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from app.models import SearchHit
from app.services.types import SearchServiceError, TemporaryServiceError


class SauceNaoClient:
    API_URL = "https://saucenao.com/search.php"

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str | None = None,
        num_results: int = 3,
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._num_results = max(1, min(num_results, 6))

    async def search(
        self,
        image: bytes,
        filename: str,
        content_type: str,
        variant_name: str = "original",
    ) -> list[SearchHit]:
        form = aiohttp.FormData()
        form.add_field("output_type", "2")
        form.add_field("numres", str(self._num_results))
        form.add_field("db", "999")
        if self._api_key:
            form.add_field("api_key", self._api_key)
        form.add_field(
            "file",
            image,
            filename=filename,
            content_type=content_type,
        )

        headers = {
            "Accept": "application/json",
            "User-Agent": "AnimeHybridBot/2.0",
        }

        try:
            async with self._session.post(
                self.API_URL,
                data=form,
                headers=headers,
            ) as response:
                payload = await self._read_json(response)
        except asyncio.TimeoutError as exc:
            raise TemporaryServiceError("SauceNAO не ответил вовремя.") from exc
        except aiohttp.ClientError as exc:
            raise TemporaryServiceError("Ошибка подключения к SauceNAO.") from exc

        if response.status == 429:
            raise SearchServiceError("SauceNAO временно ограничил запросы.")
        if response.status >= 500:
            raise TemporaryServiceError("SauceNAO временно недоступен.")
        if response.status >= 400:
            raise SearchServiceError("Ошибка SauceNAO.")

        raw_results = payload.get("results") or []
        if not isinstance(raw_results, list):
            return []

        hits: list[SearchHit] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            header = item.get("header") or {}
            data = item.get("data") or {}

            similarity = _to_score(header.get("similarity"))
            title = (
                data.get("title")
                or data.get("eng_name")
                or data.get("jp_name")
                or data.get("source")
                or "Источник не найден"
            )

            character = data.get("member_name") or data.get("characters")
            source_site = data.get("source") or data.get("creator") or data.get("author_name")

            links: list[tuple[str, str]] = []
            for url in data.get("ext_urls") or []:
                if isinstance(url, str) and url.startswith("http"):
                    links.append(("Источник", url))
            anidb = data.get("anidb_aid")
            mal_id = data.get("mal_id")
            if anidb:
                links.append(("AniDB", f"https://anidb.net/anime/{anidb}"))
            if mal_id:
                links.append(("MyAnimeList", f"https://myanimelist.net/anime/{mal_id}"))

            note_parts = []
            if character:
                note_parts.append(f"Персонаж: {character}")
            if source_site:
                note_parts.append(f"Источник: {source_site}")

            hits.append(
                SearchHit(
                    engine="SauceNAO",
                    title=str(title),
                    similarity=similarity,
                    subtitle=None,
                    preview_image=str(header.get("thumbnail") or "") or None,
                    links=tuple(links[:3]),
                    note=" | ".join(note_parts) if note_parts else None,
                    variant=variant_name,
                )
            )

        hits.sort(key=lambda item: item.similarity or 0, reverse=True)
        return hits

    @staticmethod
    async def _read_json(response: aiohttp.ClientResponse) -> dict[str, Any]:
        try:
            payload = await response.json(content_type=None)
        except Exception as exc:
            body = (await response.text())[:300]
            raise TemporaryServiceError(f"Некорректный ответ SauceNAO: {body}") from exc

        if not isinstance(payload, dict):
            raise TemporaryServiceError("SauceNAO вернул неизвестный формат.")
        return payload


def _to_score(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number > 1:
        if number <= 100:
            return number / 100
    return max(0.0, min(1.0, number))
