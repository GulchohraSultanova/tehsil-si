"""
Təhlil Sİ — server (si.fazgi.com).

Statik səhifəni verir və brauzerdən gələn sorğunu modelə ötürür:
GEMINI_API_KEY varsa Google Gemini (pulsuz plan), yoxdursa Claude API.
Kalkulyator aləti brauzerdə işləyir; server yalnız modelə müraciət edir.

İşə salma:
    GEMINI_API_KEY=... python3 app.py         (default port 5097)
    ANTHROPIC_API_KEY=... python3 app.py
"""

import json
import os
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import anthropic

import gemini

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5097"))
STATIC = Path(__file__).resolve().parent / "static"
MODEL = "claude-opus-5-5"
MAX_TOKENS = 64000
MAX_BODY = 20 * 1024 * 1024       # şəkillərlə birlikdə 20 MB
RATE_LIMIT = 60                   # bir IP üçün saatda sorğu sayı
RATE_WINDOW = 3600

FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/claude-shim.js": ("claude-shim.js", "text/javascript; charset=utf-8"),
}

# Workspace-ə bağlı olmayan açar üçün ANTHROPIC_WORKSPACE_ID (wrkspc_...) verilməlidir
WORKSPACE = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
client = anthropic.Anthropic(
    max_retries=2,
    default_headers={"anthropic-workspace-id": WORKSPACE} if WORKSPACE else None,
) if os.environ.get("ANTHROPIC_API_KEY") and not gemini.KEY else None
GEMINI_MODELS = gemini.pick_models() if gemini.KEY else None

_hits = defaultdict(deque)
_hits_lock = threading.Lock()


def rate_ok(ip):
    now = time.time()
    with _hits_lock:
        q = _hits[ip]
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return False
        q.append(now)
        return True


def error_code(e):
    if isinstance(e, anthropic.RateLimitError):
        return "rate_limited"
    if isinstance(e, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return "sampling_disabled"
    if isinstance(e, anthropic.BadRequestError):
        msg = str(e).lower()
        if "too long" in msg or "too large" in msg:
            return "prompt_too_large"
        if "image" in msg:
            return "image_rejected"
    return "upstream_error"


class Handler(BaseHTTPRequestHandler):
    server_version = "TehlilSI"

    def log_message(self, fmt, *args):
        print("%s %s" % (self.client_ip(), fmt % args), flush=True)

    def client_ip(self):
        fwd = self.headers.get("X-Forwarded-For", "")
        return fwd.split(",")[0].strip() or self.client_address[0]

    def send_json(self, status, obj):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/status":
            return self.send_json(200, {"ready": client is not None or GEMINI_MODELS is not None})
        if path not in FILES:
            return self.send_json(404, {"code": "not_found"})
        name, ctype = FILES[path]
        data = (STATIC / name).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/api/sample":
            return self.send_json(404, {"code": "not_found"})
        if client is None and GEMINI_MODELS is None:
            return self.send_json(503, {"code": "sampling_disabled"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            return self.send_json(413, {"code": "prompt_too_large"})
        if not rate_ok(self.client_ip()):
            return self.send_json(429, {"code": "rate_limited"})
        try:
            req = json.loads(self.rfile.read(length))
            messages = req["messages"]
            tools = req.get("tools") or []
            assert isinstance(messages, list) and messages and isinstance(tools, list)
        except Exception:
            return self.send_json(400, {"code": "upstream_error"})

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def emit(event, data):
            self.wfile.write(f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()

        params = dict(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=messages,
            output_config={"effort": "high" if req.get("deep") else "medium"},
            betas=["server-side-fallback-2026-07-01"],
            extra_body={"fallbacks": "default"},
        )
        if tools:
            params["tools"] = tools
        try:
            if GEMINI_MODELS:
                emit("done", gemini.stream(GEMINI_MODELS, messages, tools, emit))
                return
            with client.beta.messages.stream(**params) as stream:
                for event in stream:
                    if event.type == "content_block_delta" and event.delta.type == "text_delta":
                        emit("text", {"text": event.delta.text})
                msg = stream.get_final_message()
            dumped = msg.model_dump(mode="json", by_alias=True, exclude_none=True)
            emit("done", {"content": dumped["content"], "stop_reason": msg.stop_reason})
        except (BrokenPipeError, ConnectionResetError):
            pass  # istifadəçi «Dayandır» basdı
        except Exception as e:
            print("API xətası:", repr(e)[:800], flush=True)
            try:
                emit("error", {"code": e.code if isinstance(e, gemini.GeminiError) else error_code(e)})
            except (BrokenPipeError, ConnectionResetError):
                pass


if __name__ == "__main__":
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    srv.daemon_threads = True
    provider = f"Gemini ({', '.join(GEMINI_MODELS)})" if GEMINI_MODELS else "Claude" if client else "YOXDUR"
    print(f"Təhlil Sİ: http://{HOST}:{PORT}  (model: {provider})", flush=True)
    srv.serve_forever()
