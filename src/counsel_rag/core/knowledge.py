# 지식 문서의 도메인 타입과 섹션 분해 규칙. 왜 core인가: 문서 구조는
# 파이프라인(수집)만이 아니라 저장소·조회 서비스도 아는 도메인 개념이다 —
# pipeline을 역참조하지 않도록 core가 소유한다.
from dataclasses import dataclass

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


def split_sections(body: str) -> list[ParsedSection]:
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
