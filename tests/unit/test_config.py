# Settings가 .env(환경변수) 오버라이드를 올바르게 받는지 검증.
# 왜: "하드코딩 금지" 원칙의 실체가 이 클래스다. 오버라이드가 깨지면
#     counsel-eval의 무코드 조합 실험(설계문서 §11)이 불가능해진다.
from pathlib import Path

from counsel_rag.config import Settings


def test_defaults_are_sane():
    s = Settings(_env_file=None)  # .env 무시하고 순수 기본값 검증
    assert s.retrieval_top_n == 20
    assert s.rerank_top_k == 5
    assert s.search_stages == "hybrid,rrf,rerank,threshold"
    assert s.api_keys == []  # 비어 있으면 인증 비활성(개발 모드)
    assert s.knowledge_dir == Path("knowledge-sample")


def test_env_override(monkeypatch):
    monkeypatch.setenv("COUNSEL_RETRIEVAL_TOP_N", "7")
    monkeypatch.setenv("COUNSEL_EMBEDDER", "fake")
    s = Settings(_env_file=None)
    assert s.retrieval_top_n == 7
    assert s.embedder == "fake"
