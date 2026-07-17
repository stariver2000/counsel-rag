# 스테이지 조립소 — settings.search_stages 문자열("hybrid,rrf,rerank,threshold")을
# 순서 그대로 스테이지 리스트로 만든다.
# 왜: 검색 기법은 계속 바뀐다. 새 기법 = 스테이지 클래스 추가 + 여기 한 줄 등록.
#     기존 코드는 건드리지 않는다 (설계문서 §7 모듈형 원칙).
from counsel_rag.config import Settings
from counsel_rag.core.ports import Reranker, VectorStore
from counsel_rag.core.stages.hybrid_retrieve import HybridRetrieve
from counsel_rag.core.stages.rerank import Rerank
from counsel_rag.core.stages.rrf_fusion import RrfFusion
from counsel_rag.core.stages.threshold_gate import ThresholdGate


def build_pipeline(settings: Settings, store: VectorStore, reranker: Reranker) -> list:
    stages = []
    for name in settings.search_stages.split(","):
        name = name.strip()
        if name == "hybrid":
            stages.append(HybridRetrieve(store=store, top_n=settings.retrieval_top_n))
        elif name == "rrf":
            stages.append(RrfFusion(k=settings.rrf_k))
        elif name == "rerank":
            stages.append(Rerank(reranker=reranker, top_k=settings.rerank_top_k))
        elif name == "threshold":
            stages.append(ThresholdGate(threshold=settings.insufficient_threshold))
        else:
            raise ValueError(f"알 수 없는 검색 스테이지: {name}")
    return stages
