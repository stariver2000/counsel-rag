# 위기 스캐너 검증 — 감지해야 할 표현과 감지하면 안 되는 일상 표현.
# 왜: 위기 감지는 이 시스템의 유일한 "항상-자동" 안전장치다 (설계문서 §8).
#     false negative(놓침)가 가장 위험하므로 대표 표현을 회귀로 고정한다.
from pathlib import Path

from counsel_rag.core.crisis import CrisisScanner

scanner = CrisisScanner(Path("data/crisis_patterns.yaml"))


def test_detects_direct_self_harm():
    alert = scanner.scan("아이가 죽고 싶다고 말했어요")
    assert alert is not None
    assert alert.category == "self_harm"
    assert any("109" in h for h in alert.hotlines)
    assert alert.guide_slug == "crisis-selfharm-signs"


def test_detects_abuse():
    alert = scanner.scan("아빠가 아이를 때려서 멍이 들었어요")
    assert alert is not None
    assert alert.category == "abuse"


def test_ignores_everyday_complaints():
    # 일상 고민은 위기가 아니다 — false positive는 신뢰를 깎는다
    assert scanner.scan("아이가 게임을 그만두지 못해요") is None
    assert scanner.scan("동생이랑 자주 싸워요") is None


def test_known_limitation_is_documented():
    # 우회 표현은 키워드 방식의 알려진 한계다 (설계문서 §8 — 2단계 보조 레이어 예약).
    # 현재는 놓치는 게 "정상 동작"임을 테스트로 명시해 둔다. 보조 레이어 도입 시
    # 이 테스트를 뒤집는다(None이 아니어야 함으로).
    assert scanner.scan("그냥 다 사라졌으면 좋겠어요") is None


def test_detects_no_space_and_conjugated_forms():
    # 왜: 모바일 입력은 띄어쓰기를 생략하고, ㅅ-불규칙 활용(긋→그었)은
    #     원형 패턴만으로는 놓친다 — 실제 흔한 표현으로 회귀 고정.
    assert scanner.scan("아이가 죽고싶다고 문자를 보냈어요") is not None
    assert scanner.scan("손목을 그었어요") is not None


def test_no_false_positive_on_common_idiom():
    # "선을 긋다"류 관용구가 오탐되지 않아야 신뢰를 유지한다
    assert scanner.scan("동생이랑 사이에 선을 그었어요") is None


def test_missing_patterns_file_fails_closed(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        CrisisScanner(tmp_path / "no-such.yaml")


def test_detects_adnominal_form():
    # 왜: 관형형("그은 상처/흔적")은 목격 서술의 흔한 형태다 — 활용형 목록에 포함.
    assert scanner.scan("손목을 그은 상처가 있어요") is not None


def test_no_false_positive_on_benign_wrist_sentences():
    # 왜: 공백 제거 매칭 + 짧은 어간의 조합은 "그네/그렇게/그림"과 충돌했었다.
    # 위기 안내 오탐은 사용자 신뢰를 깎는다 — 무해 문장 회귀 고정.
    assert scanner.scan("손목을 그네에서 다쳤어요") is None
    assert scanner.scan("손목을 그렇게 심하게 다치지는 않았어요") is None
    assert scanner.scan("손목을 그림으로 표현했어요") is None


def test_malformed_patterns_file_fails_closed(tmp_path):
    import pytest

    bad = tmp_path / "bad.yaml"
    bad.write_text("just a string, no categories key")
    with pytest.raises((KeyError, TypeError)):
        CrisisScanner(bad)


def test_guide_returns_category_info():
    # API 층(/v1/crisis/{category})이 텍스트 매칭 없이 바로 조회하는 경로.
    guide = scanner.guide("self_harm")
    assert guide is not None
    assert guide["category"] == "self_harm"
    assert guide["guide_slug"] == "crisis-selfharm-signs"
    assert any("109" in h for h in guide["hotlines"])


def test_guide_returns_none_for_unknown_category():
    assert scanner.guide("unknown") is None
