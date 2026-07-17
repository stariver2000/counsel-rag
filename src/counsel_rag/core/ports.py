"""도메인 타입과 인터페이스(Protocol) 정의 — core가 의존하는 유일한 계약.
왜: 임베딩·저장소 구현을 갈아끼우는 날(원격 임베딩 서버, 다른 벡터DB)
    core를 열지 않기 위해서다 (설계문서 §4 의존 방향 규칙).
"""
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Embedding:
    """BGE-M3 모델의 hybrid 임베딩 표현."""
    dense: list[float]              # BGE-M3 dense 벡터 (1024차원)
    sparse: dict[str, float]        # BGE-M3 lexical weights {token_id: weight}


@dataclass
class SearchQuery:
    """검색 요청의 도메인 모델. text는 필수, 나머지는 선택."""
    text: str
    dense: list[float] | None = None
    sparse: dict[str, float] | None = None
    targets: list[str] | None = None    # 예: ["boy"] — store가 common을 자동 포함
    category: str | None = None
    age: int | None = None


@dataclass
class RetrievedChunk:
    """검색된 문서 청크. 디폴트로 score=0.0, ranks={} 사용."""
    chunk_id: int
    document_slug: str
    doc_title: str
    target_label: str               # 사람이 읽는 대상 라벨 (예: "남아")
    heading: str
    text: str
    score: float = 0.0
    # 단계별 랭킹 기록 {"dense": 0, "sparse": 3} — RRF 융합의 입력
    ranks: dict[str, int] = field(default_factory=dict)


class Embedder(Protocol):
    """텍스트를 Embedding으로 변환하는 포트."""
    def embed(self, texts: list[str]) -> list[Embedding]: ...


class Reranker(Protocol):
    """쿼리-본문 관련도를 점수화하는 포트."""
    def score(self, query: str, texts: list[str]) -> list[float]:
        """쿼리-본문 관련도. 0~1로 정규화된 값을 돌려준다 (threshold 비교 가능해야 함)."""
        ...


class VectorStore(Protocol):
    """Dense·Sparse 검색을 제공하는 저장소 포트."""
    def dense_search(self, query: SearchQuery, top_n: int) -> list[RetrievedChunk]: ...
    def sparse_search(self, query: SearchQuery, top_n: int) -> list[RetrievedChunk]: ...
