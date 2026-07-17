# 임계 게이트 — 최종 점수 미달 청크를 버린다. 전부 버려지면 상위 층이
# insufficient_knowledge로 해석한다 (설계문서 §7: 틀린 조언보다 "모른다"가 안전).
# 주의: threshold는 직전 스테이지의 점수 스케일에 의존한다 — rerank 뒤라면
#      rerank 점수, rerank를 뺐다면 RRF 점수(훨씬 작음)와 비교되므로 그에 맞게 조정한다.
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
