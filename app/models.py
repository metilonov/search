from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AnimeTitles:
    native: str | None = None
    romaji: str | None = None
    english: str | None = None

    def primary(self) -> str:
        return self.english or self.romaji or self.native or "Название не найдено"

    def alternatives(self) -> list[str]:
        primary = self.primary()
        result: list[str] = []
        for value in (self.romaji, self.native, self.english):
            if value and value != primary and value not in result:
                result.append(value)
        return result


@dataclass(frozen=True, slots=True)
class TraceMatch:
    anilist_id: int
    mal_id: int | None
    is_adult: bool
    titles: AnimeTitles
    synonyms: tuple[str, ...]
    episode: Any
    time_from: float
    time_to: float
    similarity: float
    preview_video: str
    preview_image: str
    filename: str

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "TraceMatch":
        anilist = payload.get("anilist")

        if isinstance(anilist, dict):
            title_data = anilist.get("title") or {}
            titles = AnimeTitles(
                native=title_data.get("native"),
                romaji=title_data.get("romaji"),
                english=title_data.get("english"),
            )
            anilist_id = int(anilist.get("id") or 0)
            raw_mal_id = anilist.get("idMal")
            mal_id = int(raw_mal_id) if raw_mal_id else None
            is_adult = bool(anilist.get("isAdult", False))
            synonyms = tuple(
                str(item)
                for item in (anilist.get("synonyms") or [])
                if item
            )
        else:
            titles = AnimeTitles()
            anilist_id = int(anilist or 0)
            mal_id = None
            is_adult = False
            synonyms = ()

        return cls(
            anilist_id=anilist_id,
            mal_id=mal_id,
            is_adult=is_adult,
            titles=titles,
            synonyms=synonyms,
            episode=payload.get("episode"),
            time_from=float(payload.get("from") or 0),
            time_to=float(payload.get("to") or 0),
            similarity=float(payload.get("similarity") or 0),
            preview_video=str(payload.get("video") or ""),
            preview_image=str(payload.get("image") or ""),
            filename=str(payload.get("filename") or ""),
        )
