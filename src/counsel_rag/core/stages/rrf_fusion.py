# RRF(Reciprocal Rank Fusion) 융합 — 점수 스케일이 다른 두 랭킹을 순위로만 합친다.
# 왜: dense 코사인과 sparse 내적은 스케일이 달라 직접 더할 수 없다.
#     score = Σ 1/(k+rank)는 스케일 무관하게 동작하는 검증된 방식이다.
from counsel_rag.core.ports import RetrievedChunk, SearchQuery


class RrfFusion:
    def __init__(self, k: int):
        self._k = k

    def run(self, query: SearchQuery, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
        for chunk in candidates:
            score = 0.0
            for rank in chunk.ranks.values():
                score += 1.0 / (self._k + rank)
            chunk.score = score
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates
