# corpus 백업 스크립트 검증 — 아카이브 생성과 세대 회전(오래된 것부터 삭제)을 확인.
# 왜 tmp_path만 사용: knowledge/·corpus/는 다른 에이전트가 작업 중인 실데이터라
#     테스트에서 건드리면 안 된다 — 가짜 corpus를 매번 새로 만든다.
import tarfile
import time

from counsel_rag.config import Settings
from counsel_rag.pipeline.backup.__main__ import run_backup


def _make_fake_corpus(tmp_path):
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "a.md").write_text("문서 A")
    (corpus_dir / "b.md").write_text("문서 B")
    return corpus_dir


def test_run_backup_creates_archive_with_contents(tmp_path):
    corpus_dir = _make_fake_corpus(tmp_path)
    backup_dir = tmp_path / "backups"  # 존재하지 않는 디렉터리 — 자동 생성 검증 겸함
    settings = Settings(
        _env_file=None, corpus_dir=corpus_dir, backup_dir=backup_dir, backup_keep=5
    )

    archive_path = run_backup(settings)

    assert archive_path.exists()
    assert archive_path.parent == backup_dir
    assert archive_path.name.startswith("corpus-") and archive_path.name.endswith(
        ".tar.gz"
    )
    with tarfile.open(archive_path, "r:gz") as tar:
        names = tar.getnames()
    assert any(name.endswith("a.md") for name in names)
    assert any(name.endswith("b.md") for name in names)


def test_run_backup_rotates_old_backups_beyond_keep_limit(tmp_path):
    corpus_dir = _make_fake_corpus(tmp_path)
    backup_dir = tmp_path / "backups"
    settings = Settings(
        _env_file=None, corpus_dir=corpus_dir, backup_dir=backup_dir, backup_keep=2
    )

    archive_paths = []
    for _ in range(3):
        archive_paths.append(run_backup(settings))
        # 파일명이 초 단위 타임스탬프라 같은 초에 실행되면 이름이 충돌한다 — 회전 검증을
        # 위해 각 실행 사이 시간을 확실히 벌려준다.
        time.sleep(1.1)

    remaining = sorted(backup_dir.glob("corpus-*.tar.gz"))
    assert len(remaining) == 2
    # 회전이 오래된 것부터 지웠는지 확인 — 가장 최근 실행분은 반드시 남아야 한다.
    assert archive_paths[-1] in remaining
