# 테스트·개발용 가짜 임베더. 모델 다운로드 없이 결정론적 벡터를 만든다.
# 왜: unit 테스트와 GPU 없는 환경에서 전체 스택(인덱싱→검색→API)을 돌리기 위해.
#     실물과 같은 계약(1024차원 dense + sparse dict)을 지켜 서로 대체 가능하다.
import hashlib
import math

from counsel_rag.core.ports import Embedding


class FakeEmbedder:
    def __init__(self, dim: int = 1024):
        self._dim = dim

    def embed(self, texts: list[str]) -> list[Embedding]:
        results = []
        for text in texts:
            results.append(Embedding(dense=self._dense(text), sparse=self._sparse(text)))
        return results

    def _dense(self, text: str) -> list[float]:
        """텍스트 해시를 시드로 한 유사-난수 벡터. 같은 입력이면 항상 같다."""
        vec = []
        for i in range(self._dim):
            h = hashlib.md5(f"{text}:{i}".encode()).digest()
            # 바이트 → -1..1 근처 실수. 품질은 무의미하고 결정론과 차원만 중요하다
            vec.append((h[0] / 255.0) * 2 - 1)
        norm = math.sqrt(sum(v * v for v in vec))
        normalized = []
        for v in vec:
            normalized.append(v / norm)
        return normalized

    def _sparse(self, text: str) -> dict[str, float]:
        """공백 분리 단어 빈도를 sparse 가중치로 사용 — 실물의 lexical weight 대역."""
        weights: dict[str, float] = {}
        for token in text.split():
            weights[token] = weights.get(token, 0.0) + 1.0
        return weights
