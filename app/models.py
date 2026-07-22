from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SearchHit:
    engine: str
    title: str
    similarity: float | None = None
    subtitle: str | None = None
    episode: str | None = None
    timestamp: str | None = None
    preview_image: str | None = None
    preview_video: str | None = None
    links: tuple[tuple[str, str], ...] = ()
    note: str | None = None
    variant: str | None = None


@dataclass(frozen=True, slots=True)
class ImageVariant:
    name: str
    filename: str
    content_type: str
    data: bytes


@dataclass(slots=True)
class SearchReport:
    trace_hits: list[SearchHit] = field(default_factory=list)
    anime_trace_hits: list[SearchHit] = field(default_factory=list)
    saucenao_hits: list[SearchHit] = field(default_factory=list)
    summary: str = ""
    low_confidence: bool = False

    def all_hits(self) -> list[SearchHit]:
        result: list[SearchHit] = []
        result.extend(self.trace_hits)
        result.extend(self.anime_trace_hits)
        result.extend(self.saucenao_hits)
        return result
