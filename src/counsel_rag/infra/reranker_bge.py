# bge-reranker-v2-m3 실물 어댑터. 원점수(logit)를 sigmoid로 0~1 정규화한다.
# 왜 정규화하는가: threshold_gate가 고정 임계값과 비교하려면 스케일이 안정해야 한다.
import math

from counsel_rag.core.ports import Reranker  # noqa: F401


class BgeReranker:
    def __init__(self, model_name: str):
        from FlagEmbedding import FlagReranker
        self._model = FlagReranker(model_name, use_fp16=True)

    def score(self, query: str, texts: list[str]) -> list[float]:
        pairs = []
        for text in texts:
            pairs.append([query, text])
        raw = self._model.compute_score(pairs)
        if not isinstance(raw, list):   # 단건이면 float로 오는 라이브러리 특성 방어
            raw = [raw]
        scores = []
        for logit in raw:
            scores.append(1.0 / (1.0 + math.exp(-float(logit))))
        return scores
