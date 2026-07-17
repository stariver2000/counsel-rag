# API 키 인증 + 인메모리 rate limit.
# 왜 인메모리인가: 단일 프로세스 서버(현 규모)에서는 충분하고 의존성이 없다.
#     다중 프로세스로 가면 redis 등으로 교체 — 이 파일만 바뀐다.
import time
from collections import deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, per_minute: int):
        self._per_minute = per_minute
        self._hits: dict[str, deque] = {}

    def check(self, key: str) -> None:
        """1분 슬라이딩 윈도 초과 시 429를 던진다."""
        now = time.monotonic()
        window = self._hits.setdefault(key, deque())
        while window and now - window[0] > 60.0:
            window.popleft()
        if len(window) >= self._per_minute:
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        window.append(now)


def enforce_auth(request: Request, api_keys: list[str], limiter: RateLimiter) -> None:
    """키 목록이 비어 있으면 인증 비활성(개발 모드). healthz는 호출부에서 제외한다."""
    if not api_keys:
        limiter.check("anonymous")
        return
    key = request.headers.get("X-API-Key")
    if key not in api_keys:
        raise HTTPException(status_code=401, detail="invalid api key")
    limiter.check(key)
