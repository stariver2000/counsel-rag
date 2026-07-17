# 문서 조회 서비스 — store는 스텁, 파일 본문은 knowledge-sample 실물로 검증.
# 왜: "전문 제공 + 접근 통제" 결정(설계 이력)에 따라 body는 md 파일에서 읽는다.
#     frontmatter(불투명 소스코드 포함)는 절대 응답에 나가면 안 된다 (설계문서 §5.3).
from counsel_rag.core.documents import DocumentsService


class StubStore:
    def get_document_meta(self, slug):
        if slug != "boy-anger-expression":
            return None
        return {
            "slug": "boy-anger-expression",
            "title": "아들의 분노 표현 지도하기",
            "targets": ["boy"], "category": "감정",
            "age_min": 5, "age_max": 13, "is_crisis": False,
            "file_path": "knowledge-sample/boy/boy-anger-expression.md",
        }

    def get_related(self, slug):
        return [{"slug": "crisis-self-harm", "title": "자해", "rel_type": "escalates_to"}]

    def list_topics(self, target):
        return [{"slug": "boy-anger-expression", "title": "분노", "category": "감정",
                 "targets": ["boy"]}]

    def stats(self):
        return {"boy": 2, "common": 1}


svc = DocumentsService(store=StubStore(), model_guide="가이드")


def test_get_document_returns_body_without_frontmatter():
    doc = svc.get_document("boy-anger-expression")
    assert doc["title"] == "아들의 분노 표현 지도하기"
    assert "## 원칙" in doc["body"]
    assert "src-001" not in doc["body"]        # 불투명 코드조차 응답에 노출 금지
    assert "sources" not in doc                # frontmatter 자체가 응답에 없음


def test_get_document_unknown_slug():
    assert svc.get_document("no-such-doc") is None


def test_summary_headings_and_principle():
    s = svc.get_summary("boy-anger-expression")
    assert s["headings"][0] == "원칙"
    assert "감정은 인정하되" in s["principle"]


def test_stats_includes_model_guide():
    st = svc.stats()
    assert st["documents_by_target"] == {"boy": 2, "common": 1}
    assert st["model_guide"] == "가이드"
