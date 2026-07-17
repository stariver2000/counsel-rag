# 검색 진입점 검증 — 위기 스캔이 "항상" 실행되고, 파이프라인 결과와 독립인지.
# 왜: 위기 안내는 모델·스테이지 구성과 무관하게 반드시 나가야 한다 (설계문서 §8).
from pathlib import Path

from counsel_rag.core.crisis import CrisisScanner
from counsel_rag.core.ports import RetrievedChunk
from counsel_rag.core.search import SearchService
from counsel_rag.infra.embedder_fake import FakeEmbedder


class EmptyStageStore:
    """검색 결과가 0건인 상황을 위한 스텁."""
    def dense_search(self, query, top_n):
        return []

    def sparse_search(self, query, top_n):
        return []


class OneHitStage:
    """파이프라인을 청크 1개로 대체하는 스텁 스테이지."""
    def run(self, query, candidates):
        return [RetrievedChunk(
            chunk_id=1, document_slug="boy-anger-expression", doc_title="분노",
            target_label="남아", heading="원칙", text="본문", score=0.9,
        )]


class LogSpyStore(EmptyStageStore):
    def __init__(self):
        self.queries = []
        self.crisis_categories = []

    def log_query(self, query, chunks):
        self.queries.append(query.text)

    def log_crisis_event(self, category):
        self.crisis_categories.append(category)


scanner = CrisisScanner(Path("data/crisis_patterns.yaml"))


def make_service(store, stages):
    return SearchService(
        embedder=FakeEmbedder(), store=store, stages=stages, scanner=scanner
    )


def test_normal_search_returns_chunks():
    store = LogSpyStore()
    svc = make_service(store, stages=[OneHitStage()])
    res = svc.search("아이가 화를 내요")
    assert res.insufficient is False
    assert res.crisis is None
    assert res.chunks[0].document_slug == "boy-anger-expression"
    assert store.queries == ["아이가 화를 내요"]   # query_log 기록 확인


def test_empty_result_marks_insufficient():
    store = LogSpyStore()
    svc = make_service(store, stages=[])
    res = svc.search("우주선 조립법")
    assert res.insufficient is True
    assert res.chunks == []


def test_crisis_alert_always_attached():
    store = LogSpyStore()
    svc = make_service(store, stages=[])   # 검색이 0건이어도
    res = svc.search("아이가 자해를 해요")
    assert res.crisis is not None          # 위기 안내는 반드시 나간다
    assert res.crisis.category == "self_harm"
    assert store.crisis_categories == ["self_harm"]  # crisis_events 기록 확인
