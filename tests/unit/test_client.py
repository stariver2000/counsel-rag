# 클라이언트 SDK 검증 — 실서버 없이 ASGITransport로 앱에 직결한다.
# 왜: 클라이언트가 실제 앱 계약과 어긋나면 즉시 여기서 깨지게 만든다.
import asyncio
import httpx
from fastapi.testclient import TestClient  # noqa: F401  (참고용)

from counsel_rag.config import Settings
from counsel_rag.api.main import create_app
from counsel_rag.client import CounselClient
from tests.unit.test_api import StubDocs, StubScanner, StubSearch


def make_client(api_keys=None) -> CounselClient:
    settings = Settings(_env_file=None, api_keys=api_keys or [])
    app = create_app(settings, search_service=StubSearch(),
                     documents_service=StubDocs(), scanner=StubScanner())

    # ASGITransport는 async-only이므로 AsyncClient와 함께 사용하고,
    # CounselClient의 동기 인터페이스를 유지하기 위해 이벤트 루프 래퍼를 사용한다.
    async def _make_async_client():
        transport = httpx.ASGITransport(app=app)
        headers = {}
        if api_keys:
            headers["X-API-Key"] = api_keys[0]
        client = httpx.AsyncClient(transport=transport, base_url="http://kb",
                                   headers=headers)
        return client

    # 이벤트 루프에서 AsyncClient 생성
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    http = loop.run_until_complete(_make_async_client())

    api_key = api_keys[0] if api_keys else None
    return CounselClient(base_url="http://kb", api_key=api_key, http=http)


def test_search_roundtrip():
    kb = make_client()
    res = kb.search("아이가 화를 내요", target="boy")
    assert res["chunks"][0]["slug"] == "boy-anger-expression"


def test_api_key_header_sent():
    kb = make_client(api_keys=["secret-1"])
    res = kb.search("아이가 화를 내요")
    assert res["insufficient"] is False   # 401이면 예외가 났을 것


def test_document_and_stats():
    kb = make_client()
    assert kb.get_document("boy-anger-expression")["slug"] == "boy-anger-expression"
    assert "documents_by_target" in kb.stats()
