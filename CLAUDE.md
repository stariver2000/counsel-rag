# counsel-rag 개발 규칙

설계 문서: counsel-rag-design repo의 specs/2026-07-17-counsel-rag-design.md (비공개)

## 아키텍처 규칙
- 의존 방향: api/pipeline → core → ports ←구현← infra. 역방향 import 금지
- core는 HTTP·SQL·모델 라이브러리를 모른다. 전부 ports의 Protocol 뒤에 숨긴다
- 어댑터 선택·조립은 config(Settings)가 결정한다

## 코딩 컨벤션
- 하드코딩 금지: 숫자·경로·모델명·스위치는 config.py 경유, .env 오버라이드
- 한 줄에 3개 이상 문법 결합(컴프리헨션+조건+언패킹 등) 금지 → 명시적 루프로 해체
- 커스텀 데코레이터 금지 (FastAPI/pydantic 필수 제외)
- 모든 파일 상단에 "무엇·왜" 2-3줄 모듈 주석. 주석은 한국어, "왜" 중심

## 테스트
- uv run pytest                  # unit만 (기본)
- uv run pytest -m integration   # docker compose up -d db 후
- uv run pytest -m slow          # 실모델 다운로드 필요
