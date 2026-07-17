# 설정(Settings)에 따라 어댑터 구현체를 고르는 조립소.
# 왜: "무엇을 쓸지"는 코드가 아니라 설정의 결정 사항이다 (설계문서 §4).
#     api와 pipeline이 같은 조립 코드를 공유해 구성 불일치를 막는다.
from counsel_rag.config import Settings
from counsel_rag.core.ports import Embedder, Reranker
from counsel_rag.infra.store_pgvector import PgVectorStore


def build_embedder(settings: Settings) -> Embedder:
    if settings.embedder == "fake":
        from counsel_rag.infra.embedder_fake import FakeEmbedder
        return FakeEmbedder()
    from counsel_rag.infra.embedder_bgem3 import BgeM3Embedder
    return BgeM3Embedder(settings.embedder_model, settings.embedder_device)


def build_store(settings: Settings) -> PgVectorStore:
    return PgVectorStore(settings.database_url)


def build_reranker(settings: Settings) -> Reranker:
    if settings.reranker == "fake":
        from counsel_rag.infra.reranker_fake import FakeReranker
        return FakeReranker()
    from counsel_rag.infra.reranker_bge import BgeReranker
    return BgeReranker(settings.reranker_model)
