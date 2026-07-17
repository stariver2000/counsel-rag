# db/*.sql을 파일명 순으로 적용하는 최소 마이그레이션 러너.
# 왜: 도구(alembic 등) 도입은 현 규모에 과설계. schema_migrations 테이블로
#     이미 적용된 파일은 건너뛰어 몇 번을 실행해도 안전(멱등)하게 한다.
import sys
from pathlib import Path

import psycopg

# db/apply.py는 스크립트라 패키지 밖 — config를 쓰기 위해 src를 경로에 추가한다
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from counsel_rag.config import Settings  # noqa: E402


def main() -> None:
    settings = Settings()
    sql_files = sorted(Path(__file__).parent.glob("[0-9]*.sql"))
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (filename text PRIMARY KEY)"
        )
        for f in sql_files:
            already = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE filename = %s", (f.name,)
            ).fetchone()
            if already:
                print(f"skip  {f.name}")
                continue
            conn.execute(f.read_text())
            conn.execute("INSERT INTO schema_migrations VALUES (%s)", (f.name,))
            print(f"apply {f.name}")
        conn.commit()


if __name__ == "__main__":
    main()
