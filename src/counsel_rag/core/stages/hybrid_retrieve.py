# 하이브리드 수집 단계 — dense·sparse 검색을 각각 수행하고 chunk_id로 병합한다.
# 왜: 의미(벡터)와 어휘(키워드)는 서로 다른 실패를 보완한다 (설계문서 §7).
from counsel_rag.core.ports import RetrievedChunk, SearchQuery, VectorStore


class HybridRetrieve:
    def __init__(self, store: VectorStore, top_n: int):
        self._store = store
        self._top_n = top_n

    def run(self, query: SearchQuery, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
        dense_hits = self._store.dense_search(query, self._top_n)
        sparse_hits = self._store.sparse_search(query, self._top_n)

        # 같은 청크가 양쪽에서 나오면 ranks를 합친다 — RRF의 입력이 된다
        merged: dict[int, RetrievedChunk] = {}
        for hit in dense_hits + sparse_hits:
            if hit.chunk_id in merged:
                merged[hit.chunk_id].ranks.update(hit.ranks)
            else:
                merged[hit.chunk_id] = hit
        return list(merged.values())
