# 공적 PDF → 텍스트 추출기.
# 왜 pypdf인가: 의존성이 가볍고 KYCI 매뉴얼류(텍스트 기반 PDF)에 충분하다.
# 표·2단 조판이 깨지는 문서를 만나면 그때 pdfplumber 추가를 검토한다 (YAGNI).
import sys
from pathlib import Path

from pypdf import PdfReader


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(pdf_path)   # 파일 없으면 FileNotFoundError 그대로 전파
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


if __name__ == "__main__":
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.write_text(extract_pdf_text(src))
    print(f"extracted {src.name} -> {out} ({out.stat().st_size} bytes)")
