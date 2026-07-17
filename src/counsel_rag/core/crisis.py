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
        # 로드 실패는 그대로 예외로 죽인다(fail-closed).
        # 왜: 패턴 파일 없이 서버가 뜨면 위기 스캔 없는 서비스가 되는데,
        #     그것이 기동 실패보다 훨씬 위험하다.
        raw = yaml.safe_load(patterns_path.read_text())
        self._categories: dict = raw["categories"]

    def scan(self, text: str) -> CrisisAlert | None:
        # 공백을 제거하고 비교한다.
        # 왜: "죽고 싶다"와 "죽고싶다"는 같은 위기 신호다 — 띄어쓰기 차이로
        #     안전장치가 뚫리면 안 된다 (false negative가 가장 위험).
        compact_text = text.replace(" ", "")
        for category, spec in self._categories.items():
            # 카테고리는 yaml 순서대로 평가 — 먼저 매칭된 것 하나만 반환한다
            # (self_harm이 최상단 = 최우선)
            for pattern in spec["patterns"]:
                compact_pattern = pattern.replace(" ", "")
                if compact_pattern in compact_text:
                    return CrisisAlert(
                        category=category,
                        headline=spec["headline"],
                        hotlines=list(spec["hotlines"]),
                        guide_slug=spec["guide_slug"],
                    )
        return None

    def guide(self, category: str) -> dict | None:
        """카테고리 코드로 안내문을 직접 조회한다 (scan과 달리 텍스트 매칭 없음).
        왜: API 층의 /v1/crisis/{category}는 이미 알려진 카테고리를 조회하므로
            scan()의 텍스트 매칭 경로를 타지 않고 바로 데이터를 꺼내야 한다.
        """
        spec = self._categories.get(category)
        if spec is None:
            return None
        return {
            "category": category,
            "headline": spec["headline"],
            "hotlines": list(spec["hotlines"]),
            "guide_slug": spec["guide_slug"],
        }
