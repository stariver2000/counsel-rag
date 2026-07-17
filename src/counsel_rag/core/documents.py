# 문서 조회 서비스 — 메타는 DB(store), 본문은 md 파일에서 읽는다.
# 왜 파일에서 읽는가: 문서가 원본이고 DB는 인덱스다 (설계문서 §6).
#     frontmatter(소스 코드 포함)는 내부 전용이므로 응답에서 제거한다 (§5.3).
import frontmatter

from counsel_rag.core.knowledge import split_sections


class DocumentsService:
    def __init__(self, store, model_guide: str):
        self._store = store
        self._model_guide = model_guide

    def get_document(self, slug: str) -> dict | None:
        meta = self._store.get_document_meta(slug)
        if meta is None:
            return None
        post = frontmatter.load(meta["file_path"])
        result = dict(meta)
        del result["file_path"]        # 서버 내부 경로는 외부에 노출하지 않는다
        result["body"] = post.content.strip()
        return result

    def get_summary(self, slug: str) -> dict | None:
        meta = self._store.get_document_meta(slug)
        if meta is None:
            return None
        post = frontmatter.load(meta["file_path"])
        sections = split_sections(post.content)
        headings = []
        for section in sections:
            headings.append(section.heading)
        principle = sections[0].text if sections else ""
        return {"slug": meta["slug"], "title": meta["title"],
                "headings": headings, "principle": principle}

    def get_related(self, slug: str) -> list[dict]:
        return self._store.get_related(slug)

    def list_topics(self, target: str | None) -> list[dict]:
        return self._store.list_topics(target)

    def stats(self) -> dict:
        return {
            "documents_by_target": self._store.stats(),
            "model_guide": self._model_guide,
        }
