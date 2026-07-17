# BGE-M3 실물 검증 — 첫 실행 시 ~2GB 모델 다운로드. slow 마커로 기본 실행에서 제외.
import pytest

from counsel_rag.infra.embedder_bgem3 import BgeM3Embedder


@pytest.mark.slow
def test_real_model_shapes():
    e = BgeM3Embedder("BAAI/bge-m3", device="auto")
    embs = e.embed(["아이가 게임을 그만두지 못해요", "형제와 자주 싸워요"])
    assert len(embs) == 2
    assert len(embs[0].dense) == 1024
    assert len(embs[0].sparse) > 0


@pytest.mark.slow
def test_similar_texts_are_closer():
    e = BgeM3Embedder("BAAI/bge-m3", device="auto")
    a, b, c = e.embed(["아이가 화를 자주 내요", "아들이 분노를 참지 못해요", "주식 시장 전망"])

    def cos(x, y):
        num = sum(p * q for p, q in zip(x, y))
        return num  # BGE-M3 dense는 정규화돼 나오므로 내적 = 코사인

    assert cos(a.dense, b.dense) > cos(a.dense, c.dense)
