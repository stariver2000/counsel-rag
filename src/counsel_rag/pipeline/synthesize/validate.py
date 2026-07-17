# 종합 산출물(synthesize 출력)의 기계 검증기 — 사람 검수(G2) 전에 형식·금칙을 자동으로 거른다.
# 왜: frontmatter 형식 오류나 실명 유출까지 검수자가 눈으로 봐야 하면 검수가 느려지고,
#     실명 유출은 특히 사람 눈으로 놓치기 쉽다 — 기계가 먼저 걸러야 한다.
from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

import frontmatter
import yaml

from counsel_rag.config import Settings
from counsel_rag.core.knowledge import TARGET_LABELS, split_sections

# frontmatter에 반드시 있어야 하는 필드 (설계문서 §5.1). age_range는 대상 전체에
# 걸치는 문서(예: common)에서는 빠질 수 있어 loader.py처럼 선택 필드로 둔다.
REQUIRED_FIELDS = [
    "id",
    "title",
    "targets",
    "category",
    "is_crisis",
    "sources",
    "reviewed",
    "version",
]
SOURCE_ID_RE = re.compile(r"^src-\d{3}$")

# 집필 규칙 5(PROMPT.md) 위반 어구 — 섹션이 조각으로 단독 반환돼도 성립해야
# 하는데, 이 어구들은 "다른 섹션을 읽어야 이해된다"는 뜻이라 그 계약을 깬다.
CROSS_REF_PHRASES = ["위에서 말했듯", "앞서 말했듯", "앞서 언급", "위 섹션", "아래 섹션"]


def validate_doc(md_path: Path) -> list[str]:
    """종합 산출물 1개를 검증해 위반 목록을 반환한다. 빈 리스트 = 통과."""
    post = frontmatter.load(md_path)
    meta = post.metadata
    violations: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in meta:
            violations.append(f"필수 필드 누락: {field}")

    for target in meta.get("targets") or []:
        if target not in TARGET_LABELS:
            valid = ", ".join(TARGET_LABELS)
            violations.append(f"targets에 유효하지 않은 값 '{target}' (유효값: {valid})")

    sources = meta.get("sources") or []
    for source in sources:
        src_id = source.get("id") if isinstance(source, dict) else source
        if not src_id or not SOURCE_ID_RE.match(str(src_id)):
            violations.append(f"sources의 id가 src-NNN 형식이 아니다: {src_id!r}")

    # 집필 규칙 3: 소스 2개 이상을 종합하는 게 원칙이고, 1개뿐이면 그 사실이
    # 검수자에게 눈에 띄어야 한다 — note가 없으면 "종합을 빼먹은 건지 정말
    # 소스가 하나뿐인 건지" 검수자가 구분할 수 없다.
    if len(sources) == 1 and "note" not in meta:
        violations.append("소스 1개인데 note 없음 (frontmatter에 note로 그 사실을 남겨라)")

    # 생성 직후에는 항상 false여야 한다 — true는 사람 검수를 이미 거쳤다는
    # 뜻이므로, 검수 전 산출물에 true가 있으면 그 자체가 사고(오기입/재사용)다.
    if meta.get("reviewed") is not False:
        violations.append("reviewed는 생성 직후 false여야 한다 (검수 통과 후에만 true)")

    if len(split_sections(post.content)) < 1:
        violations.append("본문에 '## ' 섹션이 1개 이상 있어야 한다")

    violations.extend(_find_real_names(post.content))
    violations.extend(_find_cross_references(post.content))

    return violations


def _find_cross_references(body: str) -> list[str]:
    """집필 규칙 5 위반(상호참조 어구) 검사."""
    violations = []
    for phrase in CROSS_REF_PHRASES:
        if phrase in body:
            violations.append(f"본문에 상호참조 어구가 있다: '{phrase}'")
    return violations


def _find_real_names(body: str) -> list[str]:
    """corpus/sources.yaml의 실명이 본문(body)에 노출됐는지 검사.

    frontmatter는 src-NNN 코드만 쓰므로 여기서 보지 않는다 — 실명이 샐 수
    있는 곳은 서브에이전트가 자유 문장으로 쓰는 본문뿐이다.
    """
    registry_path = Settings().corpus_dir / "sources.yaml"
    if not registry_path.exists():
        # 왜 위반이 아닌 경고인가: 레지스트리는 git 밖 비공개 파일이라 일부
        # 테스트/부분 환경에는 아예 없을 수 있다. 없다고 검증 자체를 실패시키면
        # 그 환경에서는 항상 통과도 실패도 아닌 상태가 되어 오히려 신뢰가 깨진다.
        warnings.warn(
            f"실명 검사 skip: {registry_path}가 없다 (레지스트리 미주입 환경)",
            stacklevel=2,
        )
        return []

    registry = yaml.safe_load(registry_path.read_text()) or {}
    violations: list[str] = []
    for src_id, info in (registry.get("sources") or {}).items():
        name = (info or {}).get("name")
        if not name:
            continue
        # (a) 원문 그대로 (b) 공백 제거 변형 — 둘 다 검사해 "홍길동 TV"
        # 처럼 띄어쓰기로 회피하는 케이스를 잡는다.
        for variant in {name, name.replace(" ", "")}:
            if variant and variant in body:
                violations.append(f"본문에 실명이 남아 있다 ({src_id}): {name}")
                break
    return violations


def main(argv: list[str]) -> int:
    """CLI: 인자로 받은 md 파일들을 검증하고 위반 목록을 출력한다."""
    exit_code = 0
    for arg in argv:
        path = Path(arg)
        try:
            violations = validate_doc(path)
        except Exception as exc:  # noqa: BLE001 — CLI 최상위: 파일 하나가 깨져도
            # 나머지 파일 검증은 계속돼야 하므로, 트레이스백 대신 사유만 보여주고
            # 그 파일만 위반 처리한다.
            exit_code = 1
            print(f"[FAIL] {path}: {exc}")
            continue
        if violations:
            exit_code = 1
            print(f"[FAIL] {path}")
            for v in violations:
                print(f"  - {v}")
        else:
            print(f"[OK] {path}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
