# KB API 파이썬 클라이언트 — 챗봇·counsel-eval·MCP가 공용으로 쓰는 SDK.
# 왜 얇게 유지하는가: 로직이 여기 스며들면 소비자마다 동작이 갈라진다.
#     HTTP 호출과 에러 변환만 한다.
import asyncio
import httpx


class CounselClient:
    def __init__(self, base_url: str, api_key: str | None = None,
                 http: httpx.Client | httpx.AsyncClient | None = None):
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
        # http 주입은 테스트(ASGITransport)용. 운영은 base_url로 실클라이언트 생성
        self._http = http or httpx.Client(base_url=base_url, headers=headers)
        self._is_async = isinstance(self._http, httpx.AsyncClient)
        if http is not None and headers:
            self._http.headers.update(headers)

    def _get(self, path: str, params: dict | None = None):
        if self._is_async:
            # AsyncClient의 경우 이벤트 루프에서 실행
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self._http.get(path, params=params))
        else:
            res = self._http.get(path, params=params)
        res.raise_for_status()
        return res.json()

    def _post(self, path: str, payload: dict):
        if self._is_async:
            # AsyncClient의 경우 이벤트 루프에서 실행
            loop = asyncio.get_event_loop()
            res = loop.run_until_complete(self._http.post(path, json=payload))
        else:
            res = self._http.post(path, json=payload)
        res.raise_for_status()
        return res.json()

    def search(self, query: str, target: str | None = None,
               category: str | None = None, age: int | None = None) -> dict:
        return self._post("/v1/search", {"query": query, "target": target,
                                         "category": category, "age": age})

    def search_situation(self, situation: str, child_age: int,
                         target: str | None = None) -> dict:
        return self._post("/v1/search/situation",
                          {"situation": situation, "child_age": child_age,
                           "target": target})

    def get_document(self, slug: str) -> dict:
        return self._get(f"/v1/documents/{slug}")

    def get_summary(self, slug: str) -> dict:
        return self._get(f"/v1/documents/{slug}/summary")

    def get_related(self, slug: str) -> list:
        return self._get(f"/v1/documents/{slug}/related")

    def list_topics(self, target: str | None = None) -> list:
        params = {}
        if target:
            params["target"] = target
        return self._get("/v1/topics", params=params)

    def crisis_guide(self, category: str) -> dict:
        return self._get(f"/v1/crisis/{category}")

    def stats(self) -> dict:
        return self._get("/v1/stats")
