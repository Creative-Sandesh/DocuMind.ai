"""Password gate and small IP limits for a single-process HTTPS LAN server."""

import hashlib
import hmac
import secrets
import time
from collections import deque
from threading import Lock
from urllib.parse import parse_qs

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse


COOKIE_NAME = "offline_learning_lan"
COOKIE_AGE_SECONDS = 12 * 60 * 60
AUTH_PATHS = {"/api/student/login", "/api/student/register", "/api/teacher/register"}
LAN_RESPONSE_HEADERS = {
    b"x-content-type-options": b"nosniff",
    b"x-frame-options": b"DENY",
    b"referrer-policy": b"no-referrer",
    b"permissions-policy": b"microphone=(self), camera=()",
    b"content-security-policy": (
        b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        b"img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; "
        b"font-src 'self' data:; object-src 'none'; base-uri 'none'; "
        b"frame-ancestors 'none'; form-action 'self'"
    ),
}


class SecurityHeaders:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.extend(LAN_RESPONSE_HEADERS.items())
                if scope.get("path", "").startswith(("/api/", "/rag/")):
                    headers.append((b"cache-control", b"no-store"))
            await send(message)

        await self.app(scope, receive, send_with_headers)


class IpLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self.hits: dict[str, deque[float]] = {}
        self.lock = Lock()

    def retry_after(self, key: str) -> int:
        now = time.monotonic()
        with self.lock:
            if len(self.hits) > 1024:
                self.hits = {name: values for name, values in self.hits.items()
                             if values and now - values[-1] < self.window_seconds}
            values = self.hits.setdefault(key, deque())
            while values and now - values[0] >= self.window_seconds:
                values.popleft()
            if len(values) >= self.limit:
                return max(1, int(self.window_seconds - (now - values[0])) + 1)
            values.append(now)
            return 0


class AuthRateLimit:
    def __init__(self, app):
        self.app = app
        self.limiter = IpLimiter(limit=12)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("method") == "POST" and scope.get("path") in AUTH_PATHS:
            client = scope.get("client")
            ip = client[0] if client else "unknown"
            retry = self.limiter.retry_after(f"{ip}:{scope['path']}")
            if retry:
                response = JSONResponse({"detail": "Too many account requests. Try again shortly."},
                                        status_code=429, headers={"Retry-After": str(retry)})
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


class LanAccessGate:
    def __init__(self, app, password: str):
        if len(password) < 12:
            raise ValueError("LAN_ACCESS_PASSWORD must contain at least 12 characters")
        self.app = app
        self.password = password
        self.secret = secrets.token_bytes(32)
        self.unlock_limiter = IpLimiter(limit=5)

    def _ticket(self) -> str:
        issued = str(int(time.time()))
        signature = hmac.new(self.secret, issued.encode(), hashlib.sha256).hexdigest()
        return f"{issued}.{signature}"

    def _authorized(self, ticket: str | None) -> bool:
        if not ticket:
            return False
        try:
            issued_text, signature = ticket.split(".", 1)
            issued = int(issued_text)
        except ValueError:
            return False
        if issued > time.time() or time.time() - issued > COOKIE_AGE_SECONDS:
            return False
        expected = hmac.new(self.secret, issued_text.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)

    @staticmethod
    def _unlock_page(error: bool = False) -> HTMLResponse:
        message = '<p role="alert">Incorrect password or too many attempts.</p>' if error else ""
        html = ("<!doctype html><html lang='en'><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<title>Open AI Learning</title><style>"
                "body{font:1rem system-ui;background:#0d1320;color:#eef2ff;min-height:100vh;"
                "display:grid;place-items:center;margin:0}main{width:min(90vw,24rem);padding:2rem;"
                "background:#182235;border-radius:1rem}input,button{box-sizing:border-box;width:100%;"
                "padding:.8rem;margin-top:.8rem;border-radius:.5rem;font:inherit}button{cursor:pointer}"
                "</style><main><h1>AI Learning</h1><p>Enter this server's LAN access password.</p>"
                f"{message}<form method='post' action='/lan/unlock'>"
                "<label for='password'>Access password</label>"
                "<input id='password' name='password' type='password' autocomplete='current-password' required>"
                "<button type='submit'>Open platform</button></form></main></html>")
        return HTMLResponse(html, status_code=401 if error else 200, headers={
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'",
        })

    @staticmethod
    async def _submitted_password(request: Request) -> str | None:
        if request.headers.get("content-type", "").split(";", 1)[0] != "application/x-www-form-urlencoded":
            return None
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 4096:
                return None
        try:
            fields = parse_qs(body.decode("utf-8"), max_num_fields=4)
            return fields.get("password", [None])[0]
        except (UnicodeDecodeError, ValueError):
            return None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive)
        path = scope.get("path", "")
        if path == "/lan/unlock":
            if scope.get("method") == "GET":
                response = self._unlock_page()
            elif scope.get("method") == "POST":
                client = scope.get("client")
                ip = client[0] if client else "unknown"
                retry = self.unlock_limiter.retry_after(ip)
                if retry:
                    response = self._unlock_page(error=True)
                    response.status_code = 429
                    response.headers["Retry-After"] = str(retry)
                else:
                    password = await self._submitted_password(request)
                    if password is not None and hmac.compare_digest(password, self.password):
                        response = RedirectResponse("/", status_code=303)
                        response.set_cookie(COOKIE_NAME, self._ticket(), max_age=COOKIE_AGE_SECONDS,
                                            secure=True, httponly=True, samesite="strict", path="/")
                        response.headers["Cache-Control"] = "no-store"
                    else:
                        response = self._unlock_page(error=True)
            else:
                response = JSONResponse({"detail": "Method not allowed"}, status_code=405)
            await response(scope, receive, send)
            return
        if not self._authorized(request.cookies.get(COOKIE_NAME)):
            if path == "/" and scope.get("method") == "GET":
                response = RedirectResponse("/lan/unlock", status_code=303)
            else:
                response = JSONResponse({"detail": "LAN access password required"}, status_code=401)
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
