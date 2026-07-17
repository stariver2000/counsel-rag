# 리랭크 단계 — cross-encoder로 쿼리·본문 쌍을 다시 채점해 상위 top_k만 남긴다.
# 왜: 1차 검색(bi-encoder)은 빠르지만 거칠다. 후보 20개 정도의 재채점이
#     최종 품질을 가장 크게 올린다는 것이 벤치마크 합의다 (설계문서 §7).
from counsel_rag.core.ports import Reranker, RetrievedChunk, SearchQuery


class Rerank:
    def __init__(self, reranker: Reranker, top_k: int):
        self._reranker = reranker
        self._top_k = top_k

    def run(self, query: SearchQuery, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not candidates:
            return candidates
        texts = []
        for chunk in candidates:
            texts.append(chunk.text)
        scores = self._reranker.score(query.text, texts)
        for chunk, score in zip(candidates, scores):
            chunk.score = score
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[: self._top_k]
