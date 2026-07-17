# 인덱서 엔드투엔드: knowledge-sample → DB. fake 임베더로 돈다.
# 왜: "DB는 md에서 언제든 재구축 가능"(설계문서 §6)의 실행 주체가 이 CLI다.
import pytest

from counsel_rag.config import Settings
from counsel_rag.infra.store_pgvector import PgVectorStore
from counsel_rag.pipeline.index.__main__ import run_index

pytestmark = pytest.mark.integration


def test_run_index_loads_sample(monkeypatch):
    monkeypatch.setenv("COUNSEL_EMBEDDER", "fake")
    settings = Settings(_env_file=None)
    count = run_index(settings)
    assert count == 3  # 픽스처 문서 3개

    store = PgVectorStore(settings.database_url)
    assert store.get_document_meta("crisis-self-harm") is not None
    # edges도 적재됐는지 확인
    related = store.get_related("boy-anger-expression")
    assert related[0]["slug"] == "crisis-self-harm"
