"""ports의 도메인 타입이 안정적으로 생성·기본값 동작하는지 확인.
왜: 모든 층이 이 타입 계약에 의존한다. 필드명 하나가 바뀌면 전 층이 깨지므로
    계약을 테스트로 고정해 둔다.
"""
from counsel_rag.core.ports import Embedding, RetrievedChunk, SearchQuery


def test_retrieved_chunk_defaults():
    c = RetrievedChunk(
        chunk_id=1, document_slug="boy-anger", doc_title="분노",
        target_label="남아", heading="원칙", text="본문",
    )
    assert c.score == 0.0
    assert c.ranks == {}


def test_search_query_optional_fields():
    q = SearchQuery(text="아이가 화를 내요")
    assert q.targets is None and q.dense is None and q.age is None


def test_embedding_shape():
    e = Embedding(dense=[0.1, 0.2], sparse={"12": 0.5})
    assert e.sparse["12"] == 0.5
