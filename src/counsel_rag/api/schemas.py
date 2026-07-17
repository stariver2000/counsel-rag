# 요청·응답 pydantic 모델 — /v1 계약의 명세.
# 왜 core 타입을 직접 노출하지 않는가: 내부 리팩터가 API 계약을 흔들지 않게
#     경계에서 형태를 고정한다 (버저닝 원칙, 설계문서 §9).
from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    target: str | None = None       # boy | teen_male
    category: str | None = None
    age: int | None = None


class SituationRequest(BaseModel):
    situation: str
    child_age: int
    target: str | None = None


class ChunkOut(BaseModel):
    doc: str        # 문서 제목
    target: str     # 대상 라벨 (예: "남아 (5-13세)")
    section: str
    content: str
    slug: str
    score: float


class CrisisAlertOut(BaseModel):
    category: str
    headline: str
    hotlines: list[str]
    guide_slug: str


class SearchOut(BaseModel):
    chunks: list[ChunkOut]
    crisis_alert: CrisisAlertOut | None
    insufficient: bool
