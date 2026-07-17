# BGE-M3 실물 임베더 — dense(1024)와 sparse(lexical weights)를 한 번에 출력한다.
# 왜: 하이브리드 검색(설계문서 §7)이 모델 하나로 되는 이유가 이 특성이다.
#     import를 __init__ 안으로 미룬 것은 FlagEmbedding(torch)이 무거워서
#     fake로 도는 테스트·개발 경로에서 로딩 비용을 치르지 않기 위함이다.
from counsel_rag.core.ports import Embedding


class BgeM3Embedder:
    def __init__(self, model_name: str, device: str):
        from FlagEmbedding import BGEM3FlagModel

        # device="auto"면 라이브러리가 cuda 가용 여부를 스스로 판단하게 둔다
        resolved_device = None if device == "auto" else device
        self._model = BGEM3FlagModel(model_name, use_fp16=True, device=resolved_device)

    def embed(self, texts: list[str]) -> list[Embedding]:
        out = self._model.encode(texts, return_dense=True, return_sparse=True)
        results = []
        for dense_vec, lex_weights in zip(out["dense_vecs"], out["lexical_weights"]):
            sparse = {}
            for token_id, weight in lex_weights.items():
                sparse[str(token_id)] = float(weight)
            results.append(Embedding(dense=[float(v) for v in dense_vec], sparse=sparse))
        return results
