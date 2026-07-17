# FakeEmbedder의 결정론·차원·sparse 형식 검증.
# 왜: unit/통합 테스트와 GPU 없는 개발 환경은 실모델 대신 fake로 돈다.
#     fake가 실물과 같은 계약(1024차원, sparse dict)을 지켜야 대체 가능하다.
from counsel_rag.infra.embedder_fake import FakeEmbedder


def test_deterministic_and_1024_dim():
    e = FakeEmbedder()
    a = e.embed(["아이가 화를 내요"])[0]
    b = e.embed(["아이가 화를 내요"])[0]
    assert a.dense == b.dense           # 같은 입력 → 같은 벡터 (테스트 재현성)
    assert len(a.dense) == 1024         # DB vector(1024)와 일치해야 한다


def test_sparse_reflects_tokens():
    e = FakeEmbedder()
    emb = e.embed(["게임 스마트폰 게임"])[0]
    # 단어 빈도가 가중치로 반영된다 — 하이브리드 검색 로직 테스트에 필요
    assert emb.sparse["게임"] == 2.0
    assert emb.sparse["스마트폰"] == 1.0


def test_different_texts_differ():
    e = FakeEmbedder()
    a = e.embed(["분노"])[0]
    b = e.embed(["게임"])[0]
    assert a.dense != b.dense
