# 검색 스테이지들의 단위 검증 — 전부 fake 의존성으로 돈다.
# 왜: 스테이지는 "끼웠다 뺄 수 있는" 모듈(설계문서 §7)이다. 각각이 독립적으로
#     옳아야 조합 실험(counsel-eval)이 의미를 갖는다.
from counsel_rag.config import Settings
from counsel_rag.core.pipeline import build_pipeline
from counsel_rag.core.ports import RetrievedChunk, SearchQuery
from counsel_rag.core.stages.hybrid_retrieve import HybridRetrieve
from counsel_rag.core.stages.rerank import Rerank
from counsel_rag.core.stages.rrf_fusion import RrfFusion
from counsel_rag.core.stages.threshold_gate import ThresholdGate
from counsel_rag.infra.reranker_fake import FakeReranker


def make_chunk(cid, slug="doc", ranks=None, score=0.0, text="본문"):
    return RetrievedChunk(
        chunk_id=cid, document_slug=slug, doc_title="제목", target_label="남아",
        heading="원칙", text=text, score=score, ranks=ranks or {},
    )


class StubStore:
    """dense/sparse가 서로 다른 순위를 내는 상황을 시뮬레이션."""
    def dense_search(self, query, top_n):
        return [make_chunk(1, ranks={"dense": 0}), make_chunk(2, ranks={"dense": 1})]

    def sparse_search(self, query, top_n):
        return [make_chunk(3, ranks={"sparse": 0}), make_chunk(1, ranks={"sparse": 1})]


def test_hybrid_merges_ranks_by_chunk_id():
    stage = HybridRetrieve(store=StubStore(), top_n=20)
    out = stage.run(SearchQuery(text="q"), [])
    by_id = {c.chunk_id: c for c in out}
    assert len(out) == 3                       # 1,2,3 (1은 병합됨)
    assert by_id[1].ranks == {"dense": 0, "sparse": 1}
    assert by_id[2].ranks == {"dense": 1}


def test_rrf_scores_and_sorts():
    chunks = [
        make_chunk(1, ranks={"dense": 0, "sparse": 1}),
        make_chunk(2, ranks={"dense": 1}),
    ]
    out = RrfFusion(k=60).run(SearchQuery(text="q"), chunks)
    # 양쪽 리스트에 다 있는 1번이 한쪽에만 있는 2번보다 높아야 한다
    assert out[0].chunk_id == 1
    expected = 1 / 60 + 1 / 61   # 1/(k+rank) 합
    assert abs(out[0].score - expected) < 1e-9


def test_rerank_reorders_and_cuts():
    chunks = [
        make_chunk(1, text="주식 시장 전망"),
        make_chunk(2, text="아이 분노 표현 지도"),
        make_chunk(3, text="아이 분노"),
    ]
    out = Rerank(reranker=FakeReranker(), top_k=2).run(
        SearchQuery(text="아이 분노 표현"), chunks
    )
    assert len(out) == 2
    assert out[0].chunk_id == 2               # 겹치는 단어가 가장 많은 것


def test_threshold_gate_filters():
    chunks = [make_chunk(1, score=0.9), make_chunk(2, score=0.1)]
    out = ThresholdGate(threshold=0.35).run(SearchQuery(text="q"), chunks)
    assert [c.chunk_id for c in out] == [1]


def test_build_pipeline_respects_settings_order():
    settings = Settings(_env_file=None, search_stages="hybrid,rrf,threshold")
    stages = build_pipeline(settings, store=StubStore(), reranker=FakeReranker())
    names = [type(s).__name__ for s in stages]
    # rerank를 빼면 리랭커 없이 조립된다 — 무코드 조합 실험의 근거
    assert names == ["HybridRetrieve", "RrfFusion", "ThresholdGate"]


def test_fake_reranker_normalized():
    scores = FakeReranker().score("아이 분노", ["아이 분노", "주식"])
    assert 0.0 <= scores[1] <= scores[0] <= 1.0
