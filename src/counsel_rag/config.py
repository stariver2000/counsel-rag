# 프로젝트 전체 설정의 단일 진입점.
# 왜: 하드코딩 금지 원칙(설계문서 §10) — 숫자·경로·모델명·스위치를 전부 .env로
#     덮어쓸 수 있어야 counsel-eval이 코드 수정 없이 조합 실험을 할 수 있다.
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="COUNSEL_")

    # --- 인프라 ---
    database_url: str = "postgresql://counsel:counsel@localhost:5433/counsel"
    knowledge_dir: Path = Path("knowledge-sample")  # 실지식 연결 시 .env에서 교체
    corpus_dir: Path = Path("corpus")

    # --- 어댑터 선택 (infra 조립 지점, 설계문서 §4) ---
    embedder: Literal["bgem3_local", "fake"] = "bgem3_local"
    embedder_model: str = "BAAI/bge-m3"
    embedder_device: str = "auto"  # cuda | cpu | auto
    reranker: Literal["bge_local", "fake"] = "bge_local"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    # --- 검색 파이프라인 조립 (설계문서 §7) ---
    search_stages: str = "hybrid,rrf,rerank,threshold"  # 쉼표 구분, 순서대로 실행
    retrieval_top_n: int = 20        # hybrid 단계에서 dense/sparse 각각 가져올 개수
    rerank_top_k: int = 5            # 최종 반환 상한
    rrf_k: int = 60                  # RRF 상수 (관례값 60)
    # 최종 점수 미달 시 insufficient_knowledge.
    # 0.05인 이유: bge-reranker-v2-m3 실측에서 관련 청크는 0.2 이상,
    # 무관 청크는 0.02 이하로 갈렸다 — 그 사이 값. 정밀 튜닝은 counsel-eval에서.
    insufficient_threshold: float = 0.05

    # --- 접근 통제 (설계문서 §9) ---
    api_keys: list[str] = []         # 비어 있으면 인증 비활성(개발 모드)
    rate_limit_per_minute: int = 60

    # --- 위기 감지 (설계문서 §8) ---
    crisis_patterns_path: Path = Path("data/crisis_patterns.yaml")

    # --- 안내 문구 ---
    model_guide: str = (
        "권장 클라이언트 모델: 최소 4B급(gemma 등) — search/get_document/list_topics 중심. "
        "related_documents·복합 워크플로는 상위 모델 권장."
    )

    # --- corpus 백업 ---
    backup_dir: Path = Path("/home/counsel/backups/counsel-corpus")
    backup_keep: int = 5    # 보관 세대 수 — 초과분은 오래된 것부터 삭제
