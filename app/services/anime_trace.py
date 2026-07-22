from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from app.models import SearchHit
from app.services.types import SearchServiceError, TemporaryServiceError


class AnimeTraceClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_url: str,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._session = session
        self._api_url = api_url
        self._api_key = api_key
        self._model = model

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
            headers["Authorization"] = f"Bearer {self._api_key}"
            headers["x-api-key"] = self._api_key

        params: dict[str, str] = {}
        if self._model:
            params["model"] = self._model

        try:
            async with self._session.post(
                self._api_url,
                data=form,
                headers=headers,
                params=params,
            ) as response:
                payload = await self._read_json(response)
        except asyncio.TimeoutError as exc:
            raise TemporaryServiceError("AnimeTrace не ответил вовремя.") from exc
        except aiohttp.ClientError as exc:
            raise TemporaryServiceError("Ошибка подключения к AnimeTrace.") from exc

        if response.status in {401, 403}:
            raise SearchServiceError("AnimeTrace отклонил запрос. Проверьте ключ API.")
        if response.status == 429:
            raise SearchServiceError("AnimeTrace временно ограничил запросы.")
        if response.status >= 500:
            raise TemporaryServiceError("AnimeTrace временно недоступен.")
        if response.status >= 400:
            raise SearchServiceError(str(payload.get("message") or payload.get("error") or "Ошибка AnimeTrace."))

        raw_results = (
            payload.get("data")
            or payload.get("results")
            or payload.get("result")
            or []
        )

        if isinstance(raw_results, dict):
            raw_results = [raw_results]
        if not isinstance(raw_results, list):
            return []

        hits: list[SearchHit] = []
        for item in raw_results[:limit]:
            if not isinstance(item, dict):
                continue

            anime_name = _pick_first(
                item,
                [
                    "anime_title",
                    "title",
                    "anime",
                    "anime_name",
                    "source_title",
                    "source",
                ],
            )
            if isinstance(anime_name, dict):
                anime_name = _pick_first(anime_name, ["title", "name", "romaji", "english", "native"])
            if not anime_name:
                anime_name = "Название не найдено"

            character = _pick_first(
                item,
                ["character", "character_name", "name"],
            )
            if isinstance(character, dict):
                character = _pick_first(character, ["name", "full_name"])
            score = _to_score(
                _pick_first(item, ["score", "similarity", "confidence", "probability"])
            )

            image_url = _pick_first(item, ["image", "preview", "thumbnail"])
            episode = _pick_first(item, ["episode", "ep"])
            note = _pick_first(item, ["note", "description"])

            links: list[tuple[str, str]] = []
            anilist_id = _pick_first(item, ["anilist_id", "anilist"])
            mal_id = _pick_first(item, ["mal_id", "myanimelist_id"])
            if anilist_id and str(anilist_id).isdigit():
                links.append(("AniList", f"https://anilist.co/anime/{anilist_id}"))
            if mal_id and str(mal_id).isdigit():
                links.append(("MyAnimeList", f"https://myanimelist.net/anime/{mal_id}"))

            extra_url = _pick_first(item, ["url", "link"])
            if extra_url and isinstance(extra_url, str) and extra_url.startswith("http"):
                links.append(("Открыть", extra_url))

            hits.append(
                SearchHit(
                    engine="AnimeTrace",
                    title=str(anime_name),
                    similarity=score,
                    subtitle=f"Персонаж: {character}" if character else None,
                    episode=str(episode) if episode is not None else None,
                    preview_image=str(image_url) if image_url else None,
                    links=tuple(links),
                    note=str(note) if note else None,
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
            raise TemporaryServiceError(f"Некорректный ответ AnimeTrace: {body}") from exc
        if not isinstance(payload, dict):
            raise TemporaryServiceError("AnimeTrace вернул неизвестный формат.")
        return payload


def _pick_first(source: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = source.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


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
