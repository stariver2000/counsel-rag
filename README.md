# counsel-rag

대상별(남아·청소년 남자) 상담지식 KB 서버. 검색 전용(LLM 없음), FastAPI + pgvector + BGE-M3.

## 개발 시작
uv sync
docker compose up -d db
uv run python db/apply.py
