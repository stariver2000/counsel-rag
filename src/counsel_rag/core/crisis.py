# 위기 신호 스캐너 — 검색 진입점에서 항상 실행되는 유일한 자동 안전장치.
# 왜 키워드 방식인가: LLM·외부 API에 의존하면 지연·비용·불확실성이 생긴다.
#     인프로세스 부분문자열 매칭은 수 ms이고 결정론적이다 (설계문서 §8).
# 알려진 한계: 우회 표현을 놓친다. 벡터 유사도 보조 레이어가 2단계로 예약돼 있다.
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class CrisisAlert:
    category: str
    headline: str
    hotlines: list[str]
    guide_slug: str


class CrisisScanner:
    def __init__(self, patterns_path: Path):
        raw = yaml.safe_load(patterns_path.read_text())
        self._categories: dict = raw["categories"]

    def scan(self, text: str) -> CrisisAlert | None:
        for category, spec in self._categories.items():
            for pattern in spec["patterns"]:
                if pattern in text:
                    return CrisisAlert(
                        category=category,
                        headline=spec["headline"],
                        hotlines=list(spec["hotlines"]),
                        guide_slug=spec["guide_slug"],
                    )
        return None
