# PgVectorStore 통합 테스트 — docker compose up -d db 필요 (integration 마커).
# 왜: SQL은 이 파일에만 존재한다(설계문서 §4). 어댑터가 계약을 지키는지
#     fake 임베더 + 픽스처 문서로 전체 왕복(적재→검색)을 검증한다.
from pathlib import Path

import pytest

from counsel_rag.config import Settings
from counsel_rag.core.ports import SearchQuery
from counsel_rag.infra.embedder_fake import FakeEmbedder
from counsel_rag.infra.store_pgvector import PgVectorStore
from counsel_rag.pipeline.index.loader import load_knowledge_dir, make_chunk_text

pytestmark = pytest.mark.integration


@pytest.fixture()
def store():
    settings = Settings(_env_file=None)
    s = PgVectorStore(settings.database_url)
    s.wipe_index()  # 테스트 독립성: documents/chunks/edges를 비우고 시작
    return s


@pytest.fixture()
def indexed(store):
    """픽스처 3문서를 fake 임베딩으로 적재한 상태."""
    embedder = FakeEmbedder()
    docs = load_knowledge_dir(Path("knowledge-sample"))
    for doc in docs:
        chunk_texts = []
        for section in doc.sections:
            chunk_texts.append(make_chunk_text(doc, section))
        embeddings = embedder.embed(chunk_texts)
        store.upsert_document(doc, chunk_texts, embeddings)
    store.upsert_edges(docs)
    return store, embedder


def test_dense_search_returns_ranked_chunks(indexed):
    store, embedder = indexed
    emb = embedder.embed(["분노 표현"])[0]
    q = SearchQuery(text="분노 표현", dense=emb.dense, sparse=emb.sparse, targets=["boy"])
    hits = store.dense_search(q, top_n=5)
    assert len(hits) > 0
    assert hits[0].ranks == {"dense": 0}
    assert hits[0].document_slug in {
        "boy-anger-expression", "boy-not-listening", "crisis-self-harm",
    }


def test_target_filter_includes_common(indexed):
    store, embedder = indexed
    emb = embedder.embed(["자해"])[0]
    q = SearchQuery(text="자해", dense=emb.dense, sparse=emb.sparse, targets=["boy"])
    hits = store.dense_search(q, top_n=20)
    slugs = {h.document_slug for h in hits}
    # crisis-self-harm은 targets=[common]이지만 boy 검색에 포함돼야 한다
    assert "crisis-self-harm" in slugs


def test_sparse_search_finds_lexical_match(indexed):
    store, embedder = indexed
    # fake sparse는 단어 빈도 — 본문에 실제로 있는 단어로 질의한다
    emb = embedder.embed(["1393"])[0]
    q = SearchQuery(text="1393", dense=emb.dense, sparse=emb.sparse)
    hits = store.sparse_search(q, top_n=5)
    assert hits[0].document_slug == "crisis-self-harm"
    assert hits[0].ranks == {"sparse": 0}


def test_upsert_is_idempotent(indexed):
    store, embedder = indexed
    docs = load_knowledge_dir(Path("knowledge-sample"))
    doc = docs[0]
    chunk_texts = []
    for section in doc.sections:
        chunk_texts.append(make_chunk_text(doc, section))
    store.upsert_document(doc, chunk_texts, embedder.embed(chunk_texts))
    # 같은 문서를 다시 넣어도 중복이 생기지 않는다 (인덱싱 멱등 원칙)
    metas = store.list_topics(None)
    slugs = [m["slug"] for m in metas]
    assert slugs.count(doc.slug) == 1


def test_meta_queries(indexed):
    store, _ = indexed
    meta = store.get_document_meta("boy-anger-expression")
    assert meta["title"] == "아들의 분노 표현 지도하기"
    related = store.get_related("boy-not-listening")
    assert {"slug": "boy-anger-expression", "title": "아들의 분노 표현 지도하기",
            "rel_type": "differentiates_to"} in related
    st = store.stats()
    assert st["boy"] == 2 and st["common"] == 1


def test_logs_do_not_crash(indexed):
    store, embedder = indexed
    emb = embedder.embed(["테스트"])[0]
    q = SearchQuery(text="테스트", dense=emb.dense, sparse=emb.sparse)
    store.log_query(q, [])
    store.log_crisis_event("self_harm")


def test_related_hidden_for_unreviewed_source(indexed):
    # 왜: "reviewed=true만 노출" 원칙은 연관관계 조회에도 적용된다 —
    #     미검수 문서를 slug로 찔러 관계 메타데이터가 새는 것을 막는다.
    store, embedder = indexed
    docs = load_knowledge_dir(Path("knowledge-sample"))
    draft = None
    for doc in docs:
        if doc.slug == "boy-not-listening":
            draft = doc
    draft.reviewed = False
    chunk_texts = []
    for section in draft.sections:
        chunk_texts.append(make_chunk_text(draft, section))
    store.upsert_document(draft, chunk_texts, embedder.embed(chunk_texts))
    store.upsert_edges(docs)
    assert store.get_related("boy-not-listening") == []
