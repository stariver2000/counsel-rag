# 임계 게이트 — 최종 점수 미달 청크를 버린다. 전부 버려지면 상위 층이
# insufficient_knowledge로 해석한다 (설계문서 §7: 틀린 조언보다 "모른다"가 안전).
from counsel_rag.core.ports import RetrievedChunk, SearchQuery


class ThresholdGate:
    def __init__(self, threshold: float):
        self._threshold = threshold

    def run(self, query: SearchQuery, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
        passed = []
        for chunk in candidates:
            if chunk.score >= self._threshold:
                passed.append(chunk)
        return passed
