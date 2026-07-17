# 실지식 스모크 — 라이브 서버(실모델+실지식)를 블랙박스로 관통하는 회귀 게이트.
# 왜 별도 파일인가: 샘플 스모크(test_smoke.py)는 fake 스택으로 배관을 검증하고,
#     이 파일은 실제 서비스 품질(의미 검색·위기 감지)을 검증한다 — 실모델·실지식이
#     필요해서 SMOKE_REAL_BASE_URL이 설정된 때만 돈다 (CI 기본 실행에서 제외).
import os
from pathlib import Path

import httpx
import pytest
import yaml

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("SMOKE_REAL_BASE_URL")

QUESTIONS = yaml.safe_load(
    (Path(__file__).parent / "questions-real.yaml").read_text()
)["questions"]


@pytest.fixture(scope="module")
def http():
    if not BASE_URL:
        pytest.skip("SMOKE_REAL_BASE_URL 미설정 — 실지식 스모크는 라이브 서버가 필요하다")
    return httpx.Client(base_url=BASE_URL, timeout=60.0)


@pytest.mark.parametrize("case", QUESTIONS, ids=lambda c: c["q"][:20])
def test_real_smoke_question(http, case):
    res = http.post("/v1/search", json={"query": case["q"], "target": case["target"]})
    assert res.status_code == 200
    body = res.json()

    if case["expect_crisis"]:
        assert body["crisis_alert"] is not None, "위기 안내 누락 — 절대 허용 불가"

    slugs = [c["slug"] for c in body["chunks"]]
    assert case["expect_slug"] in slugs, (
        f"기대 문서 미포함: {case['expect_slug']} not in {slugs}"
    )
