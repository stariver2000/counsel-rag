# 클라이언트 SDK 검증 — 실서버 없이 TestClient로 앱에 직결한다.
# 왜: 클라이언트가 실제 앱 계약과 어긋나면 즉시 여기서 깨지게 만든다.
from fastapi.testclient import TestClient

from counsel_rag.config import Settings
from counsel_rag.api.main import create_app
from counsel_rag.client import CounselClient
from tests.unit.test_api import StubDocs, StubScanner, StubSearch


def make_client(api_keys=None) -> CounselClient:
    settings = Settings(_env_file=None, api_keys=api_keys or [])
    app = create_app(settings, search_service=StubSearch(),
                     documents_service=StubDocs(), scanner=StubScanner())
    # TestClient는 httpx.Client 서브클래스 — ASGI 앱에 동기로 직결된다.
    # 왜: client.py에 async 분기를 넣지 않고 실앱 왕복을 테스트하기 위한
    #     테스트 전용 주입 경로.
    http = TestClient(app, base_url="http://kb")
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
