# 종합 산출물 기계 검증기 — 사람 검수(G2) 전에 형식·금칙을 자동으로 거른다.
# 왜: 검수자가 형식 오류까지 봐야 하면 검수가 느려지고, 실명 유출은
#     사람 눈으로 놓치기 쉽다.
from pathlib import Path

from counsel_rag.pipeline.synthesize.validate import validate_doc

GOOD = """---
id: test-doc
title: 테스트 문서
targets: [boy]
category: 감정
age_range: [5, 13]
is_crisis: false
sources:
  - {id: src-001, items: ["ch03"]}
reviewed: false
version: 1
---

## 원칙
내용이 있다.
"""


def _write(tmp_path, text):
    p = tmp_path / "doc.md"
    p.write_text(text)
    return p


def test_good_doc_passes(tmp_path):
    assert validate_doc(_write(tmp_path, GOOD)) == []


def test_reviewed_true_is_violation(tmp_path):
    bad = GOOD.replace("reviewed: false", "reviewed: true")
    violations = validate_doc(_write(tmp_path, bad))
    assert any("reviewed" in v for v in violations)


def test_invalid_target_is_violation(tmp_path):
    bad = GOOD.replace("targets: [boy]", "targets: [girl]")
    assert validate_doc(_write(tmp_path, bad)) != []


def test_real_name_in_body_is_violation(tmp_path, monkeypatch):
    # sources.yaml에서 실명 목록을 읽는다 — 테스트는 임시 레지스트리 주입
    reg = tmp_path / "sources.yaml"
    reg.write_text("sources:\n  src-001: {name: 홍길동TV}\n")
    monkeypatch.setenv("COUNSEL_CORPUS_DIR", str(tmp_path))
    bad = GOOD.replace("내용이 있다.", "홍길동TV에서 말하길 내용이 있다.")
    violations = validate_doc(_write(tmp_path, bad))
    assert any("실명" in v for v in violations)
