# PDF 추출기 검증 — 실PDF 픽스처 대신 pypdf로 즉석 생성한 최소 PDF 사용.
# 왜: 공적 PDF를 repo에 커밋할 수 없고(저작권·용량), 추출기의 계약
#     (텍스트 연결·빈페이지 skip)만 고정하면 충분하다.
from pathlib import Path

from pypdf import PdfWriter

from counsel_rag.pipeline.collect.pdf_extract import extract_pdf_text


def _make_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)   # 빈 페이지 (skip 대상)
    path.write_bytes(b"")
    with path.open("wb") as f:
        writer.write(f)


def test_blank_pages_are_skipped(tmp_path):
    pdf = tmp_path / "blank.pdf"
    _make_pdf(pdf)
    text = extract_pdf_text(pdf)
    assert text == ""      # 빈 페이지만 있으면 빈 문자열


def test_missing_file_raises(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        extract_pdf_text(tmp_path / "no.pdf")
