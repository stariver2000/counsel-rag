# counsel-rag

대상별(남아·청소년 남자) 상담지식 KB 서버. 검색 전용 — 답변 생성(LLM)은 소비자(챗봇)의 몫이다.

## 특징
- 하이브리드 검색: BGE-M3 dense+sparse → RRF → bge-reranker-v2-m3 → top-5
- 위기 신호 자동 감지: 모든 검색에서 서버가 자동 스캔, 감지 시 전문기관 안내를 응답에 강제 포함
- 지식 문서(markdown)가 원본, DB는 재구축 가능한 인덱스
- 검색 단계는 .env로 조립/해체 가능 (`COUNSEL_SEARCH_STAGES`)

## 권장 클라이언트 모델
최소 4B급(gemma 등) — search/get_document/list_topics 중심.
연관 문서 탐색·복합 워크플로는 상위 모델(Claude 등) 권장.

## 시작하기
```bash
uv sync
cp .env.example .env
docker compose up -d db
uv run python db/apply.py
uv run python -m counsel_rag.pipeline.index          # 지식 인덱싱
uv run uvicorn counsel_rag.api.main:app_factory --factory --port 8100
```

## 테스트
```bash
uv run pytest                    # unit
uv run pytest -m integration     # DB 필요 (스모크 포함)
uv run pytest -m slow            # 실모델 다운로드 필요
```

## 지식 데이터
`knowledge-sample/`은 형식 예시(창작 내용)다. 실제 지식은 별도 private 저장소에서
관리하며 `.env`의 `COUNSEL_KNOWLEDGE_DIR`로 연결한다.

이 서비스는 전문 심리상담이 아니며, 위기 상황에서는 자살예방 상담전화 1393,
청소년 전화 1388 등 전문기관에 연락해야 한다.
