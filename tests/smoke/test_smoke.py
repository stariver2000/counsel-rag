# 스모크: 실제 인덱싱된 DB + 실제 앱을 관통하는 10문 회귀.
# 실행 전제: docker compose up -d db && (fake 또는 실물로) 인덱싱 완료.
# 왜 integration 마커인가: DB가 필요하기 때문. 실모델이 아닌 fake 어댑터로도
#     "배관이 연결됐는가"는 충분히 검증된다. 실모델 스모크는 -m slow 환경변수로.
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from counsel_rag.config import Settings
from counsel_rag.api.main import create_app
from counsel_rag.pipeline.index.__main__ import run_index

pytestmark = pytest.mark.integration

QUESTIONS = yaml.safe_load(
    (Path(__file__).parent / "questions.yaml").read_text()
)["questions"]


@pytest.fixture(scope="module")
def client():
    # fake 어댑터로 인덱싱부터 서빙까지 같은 설정으로 맞춘다
    settings = Settings(_env_file=None, embedder="fake", reranker="fake",
                        insufficient_threshold=0.0)
    run_index(settings)
    app = create_app(settings)
    return TestClient(app)


@pytest.mark.parametrize("case", QUESTIONS, ids=lambda c: c["q"][:20])
def test_smoke_question(client, case):
    res = client.post("/v1/search",
                      json={"query": case["q"], "target": case["target"]})
    assert res.status_code == 200
    body = res.json()

    if case["expect_crisis"]:
        assert body["crisis_alert"] is not None, "위기 안내 누락 — 절대 허용 불가"

    slugs = [c["slug"] for c in body["chunks"]]
    assert case["expect_slug"] in slugs, (
        f"기대 문서 미포함: {case['expect_slug']} not in {slugs}"
    )
