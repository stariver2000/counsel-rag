# API 층 검증 — 서비스는 스텁 주입, HTTP 계약(경로·상태코드·인증·형식)만 본다.
# 왜: api/는 껍데기다(설계문서 §4). 로직 테스트는 core에서 끝났고
#     여기서는 "계약이 깨지지 않는가"만 회귀로 고정한다.
from fastapi.testclient import TestClient

from counsel_rag.config import Settings
from counsel_rag.api.main import create_app
from counsel_rag.core.crisis import CrisisAlert
from counsel_rag.core.ports import RetrievedChunk
from counsel_rag.core.search import SearchResponse


class StubSearch:
    def search(self, text, targets=None, category=None, age=None):
        chunk = RetrievedChunk(
            chunk_id=1, document_slug="boy-anger-expression",
            doc_title="아들의 분노 표현 지도하기", target_label="남아 (5-13세)",
            heading="원칙", text="본문", score=0.9,
        )
        crisis = None
        if "자해" in text:
            crisis = CrisisAlert(
                category="self_harm", headline="위기 안내",
                hotlines=["1393"], guide_slug="crisis-self-harm",
            )
        return SearchResponse(chunks=[chunk], crisis=crisis, insufficient=False)


class StubDocs:
    def get_document(self, slug):
        if slug != "boy-anger-expression":
            return None
        return {"slug": slug, "title": "분노", "targets": ["boy"], "category": "감정",
                "age_min": 5, "age_max": 13, "is_crisis": False, "body": "## 원칙"}

    def get_summary(self, slug):
        return {"slug": slug, "title": "분노", "headings": ["원칙"], "principle": "p"}

    def get_related(self, slug):
        return []

    def list_topics(self, target):
        return [{"slug": "boy-anger-expression", "title": "분노",
                 "category": "감정", "targets": ["boy"]}]

    def stats(self):
        return {"documents_by_target": {"boy": 2}, "model_guide": "g"}


class StubScanner:
    def guide(self, category):
        if category != "self_harm":
            return None
        return {"category": "self_harm", "headline": "위기 안내",
                "hotlines": ["1393"], "guide_slug": "crisis-self-harm"}


def make_client(**settings_kwargs) -> TestClient:
    settings = Settings(_env_file=None, **settings_kwargs)
    app = create_app(settings, search_service=StubSearch(),
                     documents_service=StubDocs(), scanner=StubScanner())
    return TestClient(app)


def test_search_contract():
    client = make_client()
    res = client.post("/v1/search", json={"query": "아이가 화를 내요", "target": "boy"})
    assert res.status_code == 200
    body = res.json()
    assert body["insufficient"] is False
    assert body["crisis_alert"] is None
    chunk = body["chunks"][0]
    assert chunk["doc"] == "아들의 분노 표현 지도하기"
    assert chunk["target"] == "남아 (5-13세)"
    assert chunk["section"] == "원칙"
    assert chunk["content"] == "본문"


def test_search_crisis_alert_present():
    client = make_client()
    res = client.post("/v1/search", json={"query": "아이가 자해를 해요"})
    assert res.json()["crisis_alert"]["hotlines"] == ["1393"]


def test_situation_search():
    client = make_client()
    res = client.post("/v1/search/situation",
                      json={"situation": "동생을 때려요", "age": 7})
    assert res.status_code == 200


def test_document_endpoints():
    client = make_client()
    assert client.get("/v1/documents/boy-anger-expression").status_code == 200
    assert client.get("/v1/documents/none").status_code == 404
    assert client.get("/v1/documents/boy-anger-expression/summary").status_code == 200
    assert client.get("/v1/documents/boy-anger-expression/related").status_code == 200
    assert client.get("/v1/topics").status_code == 200
    assert client.get("/v1/stats").status_code == 200
    assert client.get("/healthz").status_code == 200


def test_crisis_guide_endpoint():
    client = make_client()
    assert client.get("/v1/crisis/self_harm").status_code == 200
    assert client.get("/v1/crisis/unknown").status_code == 404


def test_api_key_required_when_configured():
    client = make_client(api_keys=["secret-1"])
    assert client.post("/v1/search", json={"query": "q"}).status_code == 401
    ok = client.post("/v1/search", json={"query": "q"},
                     headers={"X-API-Key": "secret-1"})
    assert ok.status_code == 200
    # healthz는 인증 없이 열려 있어야 한다 (모니터링용)
    assert client.get("/healthz").status_code == 200


def test_rate_limit():
    client = make_client(api_keys=["k"], rate_limit_per_minute=3)
    headers = {"X-API-Key": "k"}
    for _ in range(3):
        assert client.post("/v1/search", json={"query": "q"},
                           headers=headers).status_code == 200
    blocked = client.post("/v1/search", json={"query": "q"}, headers=headers)
    assert blocked.status_code == 429


def test_rate_limit_under_concurrency():
    # 왜: 락 없는 정리→확인→기록은 동시 요청에서 한도를 뚫는다(TOCTOU) —
    #     스레드 20개가 동시에 쳐도 허용 수가 정확히 한도와 같아야 한다.
    from concurrent.futures import ThreadPoolExecutor

    from fastapi import HTTPException

    from counsel_rag.api.security import RateLimiter

    limiter = RateLimiter(per_minute=5)

    def hit():
        try:
            limiter.check("k")
            return 1
        except HTTPException:
            return 0

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(lambda _: hit(), range(20)))
    assert sum(results) == 5
