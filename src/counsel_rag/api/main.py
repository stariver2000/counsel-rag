# FastAPI 앱 조립 — 서비스 주입(테스트) 또는 assemble 실물 조립(운영).
# 라우터를 파일로 쪼개지 않은 이유: 엔드포인트 9개 규모에서는 한 파일이
# 더 읽기 쉽다. 늘어나면 routers/로 분리한다 (YAGNI).
from fastapi import FastAPI, HTTPException, Request

from counsel_rag.api import schemas
from counsel_rag.api.security import RateLimiter, enforce_auth
from counsel_rag.config import Settings


def create_app(
    settings: Settings,
    search_service=None,
    documents_service=None,
    scanner=None,
) -> FastAPI:
    # 주입이 없으면 실물 조립 (임베더·리랭커 로딩이 무거워 조건 분기)
    if search_service is None or documents_service is None or scanner is None:
        from counsel_rag.core.crisis import CrisisScanner
        from counsel_rag.core.documents import DocumentsService
        from counsel_rag.core.search_pipeline import build_pipeline
        from counsel_rag.core.search import SearchService
        from counsel_rag.infra.assemble import build_embedder, build_reranker, build_store

        store = build_store(settings)
        crisis_scanner = CrisisScanner(settings.crisis_patterns_path)
        stages = build_pipeline(settings, store=store,
                                reranker=build_reranker(settings))
        search_service = SearchService(
            embedder=build_embedder(settings), store=store,
            stages=stages, scanner=crisis_scanner,
        )
        documents_service = DocumentsService(
            store=store, model_guide=settings.model_guide,
        )
        # CrisisScanner가 guide()를 공개 메서드로 제공하므로 어댑터가 필요 없다
        # (Task 10 리팩터 — 사설 _categories 접근 대신 공개 계약을 쓴다).
        scanner = crisis_scanner

    app = FastAPI(title="counsel-rag KB", version="0.1.0")
    limiter = RateLimiter(settings.rate_limit_per_minute)

    def _auth(request: Request) -> None:
        enforce_auth(request, settings.api_keys, limiter)

    def _to_search_out(res) -> schemas.SearchOut:
        chunks = []
        for c in res.chunks:
            chunks.append(schemas.ChunkOut(
                doc=c.doc_title, target=c.target_label, section=c.heading,
                content=c.text, slug=c.document_slug, score=c.score,
            ))
        crisis = None
        if res.crisis is not None:
            crisis = schemas.CrisisAlertOut(
                category=res.crisis.category, headline=res.crisis.headline,
                hotlines=res.crisis.hotlines, guide_slug=res.crisis.guide_slug,
            )
        return schemas.SearchOut(chunks=chunks, crisis_alert=crisis,
                                 insufficient=res.insufficient)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.post("/v1/search", response_model=schemas.SearchOut)
    def search(req: schemas.SearchRequest, request: Request):
        _auth(request)
        targets = [req.target] if req.target else None
        res = search_service.search(req.query, targets=targets,
                                    category=req.category, age=req.age)
        return _to_search_out(res)

    @app.post("/v1/search/situation", response_model=schemas.SearchOut)
    def search_situation(req: schemas.SituationRequest, request: Request):
        _auth(request)
        targets = [req.target] if req.target else None
        res = search_service.search(req.situation, targets=targets,
                                    age=req.age)
        return _to_search_out(res)

    @app.get("/v1/documents/{slug}")
    def get_document(slug: str, request: Request):
        _auth(request)
        doc = documents_service.get_document(slug)
        if doc is None:
            raise HTTPException(status_code=404, detail="document not found")
        return doc

    @app.get("/v1/documents/{slug}/summary")
    def get_summary(slug: str, request: Request):
        _auth(request)
        summary = documents_service.get_summary(slug)
        if summary is None:
            raise HTTPException(status_code=404, detail="document not found")
        return summary

    @app.get("/v1/documents/{slug}/related")
    def get_related(slug: str, request: Request):
        _auth(request)
        return documents_service.get_related(slug)

    @app.get("/v1/topics")
    def list_topics(request: Request, target: str | None = None):
        _auth(request)
        return documents_service.list_topics(target)

    @app.get("/v1/crisis/{category}")
    def crisis_guide(category: str, request: Request):
        _auth(request)
        guide = scanner.guide(category)
        if guide is None:
            raise HTTPException(status_code=404, detail="unknown crisis category")
        return guide

    @app.get("/v1/stats")
    def stats(request: Request):
        _auth(request)
        return documents_service.stats()

    return app


def app_factory() -> FastAPI:
    """uvicorn --factory 진입점 — 운영 기동용."""
    return create_app(Settings())
