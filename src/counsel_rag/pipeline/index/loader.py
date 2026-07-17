# knowledge 문서(md + frontmatter)를 파싱해 섹션 단위 청크로 나누는 로더.
# 왜: 문서가 원본이고 DB는 재구축 가능한 인덱스(설계문서 §6) — 그 변환의 첫 절반이다.
#     섹션(## 헤딩)이 곧 청크 단위인 이유는 집필 규칙 §5.2 "섹션 단위 완결" 때문.
from dataclasses import dataclass
from pathlib import Path

import frontmatter

TARGET_LABELS = {"boy": "남아", "teen_male": "청소년 남자", "common": "공통"}


@dataclass
class ParsedSection:
    heading: str
    text: str


@dataclass
class ParsedDoc:
    slug: str
    title: str
    targets: list[str]
    category: str
    age_min: int | None
    age_max: int | None
    is_crisis: bool
    reviewed: bool
    edges: list[tuple[str, str]]   # (대상 slug, rel_type)
    file_path: str
    sections: list[ParsedSection]


def load_knowledge_dir(path: Path) -> list[ParsedDoc]:
    """디렉터리를 재귀 순회하며 모든 지식 문서를 파싱한다.

    '_'로 시작하는 파일(_taxonomy.yaml 등)은 문서가 아니므로 제외한다.
    reviewed 필터링은 여기서 하지 않는다 — 로더는 '전부 읽기'만 책임지고,
    노출 여부 판단은 검색 쿼리(store)의 책임이다.
    """
    docs = []
    for md_path in sorted(path.rglob("*.md")):
        if md_path.name.startswith("_"):
            continue
        docs.append(_parse_doc(md_path))
    return docs


def _parse_doc(md_path: Path) -> ParsedDoc:
    post = frontmatter.load(md_path)
    meta = post.metadata

    age_range = meta.get("age_range")
    age_min = age_range[0] if age_range else None
    age_max = age_range[1] if age_range else None

    # edges frontmatter는 [{to: slug, type: rel}] 형태 — 튜플 리스트로 정규화
    edges = []
    for e in meta.get("edges", []):
        edges.append((e["to"], e["type"]))

    return ParsedDoc(
        slug=meta["id"],
        title=meta["title"],
        targets=list(meta["targets"]),
        category=meta["category"],
        age_min=age_min,
        age_max=age_max,
        is_crisis=bool(meta.get("is_crisis", False)),
        reviewed=bool(meta.get("reviewed", False)),
        edges=edges,
        file_path=str(md_path),
        sections=_split_sections(post.content),
    )


def _split_sections(body: str) -> list[ParsedSection]:
    """본문을 '## ' 헤딩 기준으로 나눈다. 헤딩 이전의 잡문은 버린다."""
    sections = []
    current_heading = None
    current_lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current_heading is not None:
                sections.append(
                    ParsedSection(current_heading, "\n".join(current_lines).strip())
                )
            current_heading = line[3:].strip()
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line)
    if current_heading is not None:
        sections.append(ParsedSection(current_heading, "\n".join(current_lines).strip()))
    return sections


def make_chunk_text(doc: ParsedDoc, section: ParsedSection) -> str:
    """청크에 맥락 헤더를 붙인다.

    왜: 조각이 단독으로 반환돼도 '누구에 대한, 무슨 상황의 지식'인지
    클라이언트 모델이 알 수 있어야 한다 (설계문서 §7). 헤더를 포함해
    임베딩하면 검색 정확도도 올라간다 (contextual retrieval).
    """
    labels = []
    for t in doc.targets:
        labels.append(TARGET_LABELS.get(t, t))
    label = "·".join(labels)
    if doc.age_min is not None:
        label = f"{label} ({doc.age_min}-{doc.age_max}세)"
    return f"[{doc.title} | {label} | {section.heading}]\n{section.text}"
