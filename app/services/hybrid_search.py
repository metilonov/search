from __future__ import annotations

import logging

from app.config import Settings
from app.models import ImageVariant, SearchHit, SearchReport
from app.services.anime_trace import AnimeTraceClient
from app.services.saucenao import SauceNaoClient
from app.services.trace_moe import TraceMoeClient
from app.services.types import SearchServiceError, TemporaryServiceError

logger = logging.getLogger(__name__)


class HybridSearchService:
    def __init__(
        self,
        settings: Settings,
        trace_client: TraceMoeClient,
        anime_trace_client: AnimeTraceClient,
        saucenao_client: SauceNaoClient,
    ) -> None:
        self.settings = settings
        self.trace_client = trace_client
        self.anime_trace_client = anime_trace_client
        self.saucenao_client = saucenao_client

    async def search(self, variants: list[ImageVariant]) -> SearchReport:
        report = SearchReport()

        trace_hits = await self._search_trace(variants)
        report.trace_hits = trace_hits[: self.settings.trace_max_results]

        best_trace = trace_hits[0] if trace_hits else None
        if best_trace and (best_trace.similarity or 0) >= self.settings.trace_confident_score:
            report.summary = (
                "✅ Найдено уверенное совпадение через trace.moe. "
                "Дополнительные движки не запускались."
            )
            report.low_confidence = False
            return report

        report.low_confidence = True
        report.summary = (
            "⚠️ Уверенного совпадения через trace.moe нет. "
            "Запущены дополнительные поиски: AnimeTrace и SauceNAO."
        )

        if self.settings.anime_trace_enabled:
            report.anime_trace_hits = await self._search_anime_trace(variants)

        if self.settings.saucenao_enabled:
            report.saucenao_hits = await self._search_saucenao(variants)

        return report

    async def _search_trace(self, variants: list[ImageVariant]) -> list[SearchHit]:
        all_hits: list[SearchHit] = []

        for variant in variants:
            try:
                hits = await self.trace_client.search(
                    image=variant.data,
                    filename=variant.filename,
                    content_type=variant.content_type,
                    variant_name=variant.name,
                    limit=self.settings.trace_max_results,
                )
            except (SearchServiceError, TemporaryServiceError) as exc:
                logger.warning("trace.moe error (%s): %s", variant.name, exc)
                continue
            all_hits.extend(hits)

        filtered = [
            hit for hit in all_hits
            if (hit.similarity or 0) >= self.settings.trace_min_score
        ]

        if not filtered:
            filtered = all_hits

        filtered.sort(key=lambda item: item.similarity or 0, reverse=True)
        return self._unique_by_identity(filtered)

    async def _search_anime_trace(self, variants: list[ImageVariant]) -> list[SearchHit]:
        all_hits: list[SearchHit] = []

        for variant in variants[:2]:
            try:
                hits = await self.anime_trace_client.search(
                    image=variant.data,
                    filename=variant.filename,
                    content_type=variant.content_type,
                    variant_name=variant.name,
                    limit=3,
                )
            except (SearchServiceError, TemporaryServiceError) as exc:
                logger.warning("AnimeTrace error (%s): %s", variant.name, exc)
                continue
            all_hits.extend(hits)

        filtered = [
            hit for hit in all_hits
            if (hit.similarity or 0) >= self.settings.anime_trace_min_score
        ]
        filtered.sort(key=lambda item: item.similarity or 0, reverse=True)
        return self._unique_by_identity(filtered)[:3]

    async def _search_saucenao(self, variants: list[ImageVariant]) -> list[SearchHit]:
        all_hits: list[SearchHit] = []

        for variant in variants[:2]:
            try:
                hits = await self.saucenao_client.search(
                    image=variant.data,
                    filename=variant.filename,
                    content_type=variant.content_type,
                    variant_name=variant.name,
                )
            except (SearchServiceError, TemporaryServiceError) as exc:
                logger.warning("SauceNAO error (%s): %s", variant.name, exc)
                continue
            all_hits.extend(hits)

        filtered = [
            hit for hit in all_hits
            if (hit.similarity or 0) >= self.settings.saucenao_min_score
        ]
        filtered.sort(key=lambda item: item.similarity or 0, reverse=True)
        return self._unique_by_identity(filtered)[:3]

    @staticmethod
    def _unique_by_identity(hits: list[SearchHit]) -> list[SearchHit]:
        seen: set[tuple[str, str, str | None]] = set()
        result: list[SearchHit] = []

        for hit in hits:
            key = (hit.engine, hit.title.casefold(), hit.subtitle)
            if key in seen:
                continue
            seen.add(key)
            result.append(hit)

        return result
