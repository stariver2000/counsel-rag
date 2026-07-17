# 인덱싱 CLI: knowledge_dir의 모든 문서를 청킹→임베딩→DB 적재한다. 멱등.
# 사용법: uv run python -m counsel_rag.pipeline.index
# 왜 전체 재적재인가: 수만 청크 규모에서는 증분 관리의 복잡성이 이득보다 크다.
from counsel_rag.config import Settings
from counsel_rag.infra.assemble import build_embedder, build_store
from counsel_rag.pipeline.index.loader import load_knowledge_dir, make_chunk_text


def run_index(settings: Settings) -> int:
    embedder = build_embedder(settings)
    store = build_store(settings)

    docs = load_knowledge_dir(settings.knowledge_dir)
    for doc in docs:
        chunk_texts = []
        for section in doc.sections:
            chunk_texts.append(make_chunk_text(doc, section))
        embeddings = embedder.embed(chunk_texts)
        store.upsert_document(doc, chunk_texts, embeddings)
        print(f"indexed {doc.slug} ({len(chunk_texts)} chunks)")
    store.upsert_edges(docs)
    print(f"done: {len(docs)} documents")
    return len(docs)


if __name__ == "__main__":
    run_index(Settings())
