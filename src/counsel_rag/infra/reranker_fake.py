# 테스트·개발용 가짜 리랭커 — 쿼리 단어와 본문의 겹침 비율을 0~1 점수로 준다.
from counsel_rag.core.ports import Reranker  # noqa: F401  (계약 명시용 import)


class FakeReranker:
    def score(self, query: str, texts: list[str]) -> list[float]:
        query_tokens = set(query.split())
        scores = []
        for text in texts:
            text_tokens = set(text.split())
            if not query_tokens:
                scores.append(0.0)
                continue
            overlap = len(query_tokens & text_tokens)
            scores.append(overlap / len(query_tokens))
        return scores
