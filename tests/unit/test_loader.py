# 지식 md 파일의 frontmatter 파싱과 섹션(## 단위) 청킹을 검증.
# 왜: 청크 = 검색·서빙의 원자 단위(설계문서 §7). 여기가 틀리면 그 뒤 전부 틀린다.
#     픽스처(knowledge-sample)를 직접 읽어 "형식 그 자체"를 회귀 고정한다.
from pathlib import Path

from counsel_rag.pipeline.index.loader import (
    TARGET_LABELS,
    load_knowledge_dir,
    make_chunk_text,
)

SAMPLE_DIR = Path("knowledge-sample")


def test_loads_three_docs_and_skips_underscore_files():
    docs = load_knowledge_dir(SAMPLE_DIR)
    slugs = sorted(d.slug for d in docs)
    # _taxonomy.yaml은 문서가 아니므로 로드되지 않아야 한다
    assert slugs == ["boy-anger-expression", "boy-not-listening", "crisis-self-harm"]


def test_frontmatter_fields():
    docs = {d.slug: d for d in load_knowledge_dir(SAMPLE_DIR)}
    anger = docs["boy-anger-expression"]
    assert anger.targets == ["boy"]
    assert anger.category == "감정"
    assert anger.age_min == 5 and anger.age_max == 13
    assert anger.reviewed is True
    assert ("crisis-self-harm", "escalates_to") in anger.edges
    crisis = docs["crisis-self-harm"]
    assert crisis.is_crisis is True
    assert crisis.edges == []  # edges 없는 문서는 빈 리스트


def test_sections_split_on_h2():
    docs = {d.slug: d for d in load_knowledge_dir(SAMPLE_DIR)}
    headings = [s.heading for s in docs["boy-anger-expression"].sections]
    assert headings[0] == "원칙"
    assert "상황을 좁히는 질문" in headings


def test_chunk_text_has_context_header():
    docs = {d.slug: d for d in load_knowledge_dir(SAMPLE_DIR)}
    doc = docs["boy-anger-expression"]
    chunk = make_chunk_text(doc, doc.sections[0])
    # 조각이 혼자 돌아다녀도 맥락을 알 수 있어야 한다 (설계문서 §7)
    assert chunk.startswith("[아들의 분노 표현 지도하기 | 남아 (5-13세) | 원칙]")


def test_target_labels():
    assert TARGET_LABELS["teen_male"] == "청소년 남자"


def test_underscore_md_files_are_skipped(tmp_path):
    # 왜: '_*.md' skip 브랜치는 실픽스처(_taxonomy.yaml은 .md가 아님)로는 검증되지 않는다.
    #     이 브랜치가 지워져도 기존 테스트가 통과하는 공백을 막는다.
    (tmp_path / "_draft.md").write_text(
        "---\nid: draft\ntitle: 초안\ntargets: [boy]\ncategory: 감정\n"
        "is_crisis: false\nreviewed: false\nversion: 1\n---\n\n## 원칙\n내용\n"
    )
    assert load_knowledge_dir(tmp_path) == []


def test_optional_fields_and_preamble_are_handled(tmp_path):
    # 왜: age_range 없는 문서(age_min=None 계약), edges 없는 문서,
    #     첫 헤딩 앞 잡문 버리기 — 셋 다 실픽스처에 없는 경로다.
    (tmp_path / "doc.md").write_text(
        "---\nid: no-age\ntitle: 나이없음\ntargets: [common]\ncategory: 감정\n"
        "is_crisis: false\nreviewed: true\nversion: 1\n---\n\n"
        "헤딩 앞 잡문은 버려져야 한다\n\n## 원칙\n본문\n"
    )
    docs = load_knowledge_dir(tmp_path)
    doc = docs[0]
    assert doc.age_min is None and doc.age_max is None
    assert doc.edges == []
    assert len(doc.sections) == 1
    assert doc.sections[0].heading == "원칙"
    assert "잡문" not in doc.sections[0].text
