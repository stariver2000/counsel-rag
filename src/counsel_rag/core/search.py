# 검색 진입점 — 위기 스캔(항상) + 스테이지 파이프라인 실행 + 운영 로그.
# 왜 위기 스캔이 파이프라인 밖인가: 스테이지는 끼웠다 뺄 수 있지만
#     안전장치는 뺄 수 있으면 안 되기 때문이다 (설계문서 §7, §8).
from dataclasses import dataclass

from counsel_rag.core.crisis import CrisisAlert, CrisisScanner
from counsel_rag.core.ports import Embedder, RetrievedChunk, SearchQuery


@dataclass
class SearchResponse:
    chunks: list[RetrievedChunk]
    crisis: CrisisAlert | None
    insufficient: bool


class SearchService:
    def __init__(self, embedder: Embedder, store, stages: list, scanner: CrisisScanner):
        self._embedder = embedder
        self._store = store
        self._stages = stages
        self._scanner = scanner

    def search(
        self,
        text: str,
        targets: list[str] | None = None,
        category: str | None = None,
        age: int | None = None,
    ) -> SearchResponse:
        # 1) 위기 스캔 — 검색 성패와 무관하게 항상 먼저
        crisis = self._scanner.scan(text)
        if crisis is not None:
            self._store.log_crisis_event(crisis.category)

        # 2) 임베딩 + 스테이지 파이프라인
        embedding = self._embedder.embed([text])[0]
        query = SearchQuery(
            text=text, dense=embedding.dense, sparse=embedding.sparse,
            targets=targets, category=category, age=age,
        )
        candidates: list[RetrievedChunk] = []
        for stage in self._stages:
            candidates = stage.run(query, candidates)

        # 3) 운영 로그 (개인 식별자 없음 — 설계문서 §6)
        self._store.log_query(query, candidates)

        return SearchResponse(
            chunks=candidates,
            crisis=crisis,
            insufficient=(len(candidates) == 0),
        )
