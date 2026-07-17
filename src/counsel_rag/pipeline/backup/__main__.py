# 백업 CLI: corpus/ 전체를 tar.gz로 묶어 backup_dir에 보관하고, backup_keep을
# 초과하는 오래된 세대는 삭제한다.
# 사용법: uv run python -m counsel_rag.pipeline.backup
# 왜 tarfile 표준 라이브러리만인가: 별도 백업 도구 의존성 없이 어떤 환경에서도
#     재현 가능한 아카이브를 만들기 위해서다(외장 디스크·클라우드 전환은 .env의
#     COUNSEL_BACKUP_DIR만 바꾸면 되도록 경로를 설정으로 분리했다).
import tarfile
from datetime import datetime
from pathlib import Path

from counsel_rag.config import Settings


def run_backup(settings: Settings) -> Path:
    settings.backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = settings.backup_dir / f"corpus-{timestamp}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        # arcname을 corpus 디렉터리 이름으로 고정 — 절대경로가 아카이브 안에
        # 그대로 박히면 복원 시 원래 경로가 달라도 헷갈리게 된다.
        tar.add(settings.corpus_dir, arcname=settings.corpus_dir.name)

    _rotate_backups(settings.backup_dir, settings.backup_keep)
    print(f"backup created: {archive_path}")
    return archive_path


def _rotate_backups(backup_dir: Path, keep: int) -> None:
    # 왜 파일명 정렬인가: corpus-YYYYMMDD-HHMMSS.tar.gz 형식이라 이름순 정렬이
    # 곧 시간순 정렬이다 — mtime을 따로 신뢰할 필요가 없다.
    backups = sorted(backup_dir.glob("corpus-*.tar.gz"))
    excess = len(backups) - keep
    if excess <= 0:
        return
    for old in backups[:excess]:
        old.unlink()
        print(f"backup rotated out: {old}")


if __name__ == "__main__":
    run_backup(Settings())
