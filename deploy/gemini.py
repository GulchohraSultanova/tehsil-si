"""
Google Gemini (pulsuz plan) üçün körpü.

Brauzer sorğunu Claude Messages formatında göndərir (bax: static/claude-shim.js).
Bu modul həmin formatı Gemini-yə çevirir və cavabı yenə Claude blokları kimi qaytarır,
ona görə səhifəyə və kalkulyatora toxunmaq lazım deyil.

Modelin xam hissələri (thought signature daxil) "gemini_parts" blokunda saxlanılır
və növbəti addımda Gemini-yə dəyişmədən qaytarılır.
"""

import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com").rstrip("/")
KEY = os.environ.get("GEMINI_API_KEY", "").strip()
TIMEOUT = 60                      # cavab gəlməsə növbəti modelə keçilir
REFUSAL = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION", "IMAGE_SAFETY"}


class GeminiError(Exception):
    def __init__(self, code, detail=""):
        super().__init__(f"{code}: {detail}")
        self.code = code


def _request(path, body=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"x-goog-api-key": KEY, "Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    try:
        return urllib.request.urlopen(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        if e.code == 429:
            raise GeminiError("rate_limited", detail)
        if e.code in (500, 503, 504):
            raise GeminiError("overloaded", f"{e.code} {detail}")
        if e.code in (401, 403) or "API key" in detail:
            raise GeminiError("sampling_disabled", detail)
        if e.code == 400 and ("too long" in detail or "exceeds" in detail):
            raise GeminiError("prompt_too_large", detail)
        raise GeminiError("upstream_error", f"{e.code} {detail}")
    except (urllib.error.URLError, TimeoutError) as e:
        raise GeminiError("overloaded", repr(e))


def _lines(r, parts):
    """Axın sətirləri; mətn başlamamış kəsilərsə «overloaded» (növbəti model sınansın)."""
    try:
        yield from r
    except (TimeoutError, OSError) as e:
        if parts:
            raise GeminiError("upstream_error", repr(e))
        raise GeminiError("overloaded", repr(e))


def pick_models():
    """Sınanacaq modellər: ən yeni stabil «flash» modelləri, sonra «flash-lite».
    GEMINI_MODEL verilibsə (vergüllə bir neçə), yalnız onlar."""
    if os.environ.get("GEMINI_MODEL"):
        return [m.strip() for m in os.environ["GEMINI_MODEL"].split(",") if m.strip()]
    try:
        with _request("/v1beta/models?pageSize=200") as r:
            models = json.load(r).get("models", [])
    except Exception as e:
        print("Gemini model siyahısı alınmadı:", repr(e), flush=True)
        return ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    bad = ("preview", "exp", "image", "tts", "live", "audio", "thinking", "8b")
    names = [
        m["name"].split("/", 1)[1] for m in models
        if "generateContent" in m.get("supportedGenerationMethods", [])
        and "flash" in m["name"] and not any(b in m["name"] for b in bad)
    ]

    def version(n):
        parts = n.split("-")
        try:
            return tuple(int(x) for x in parts[1].split("."))
        except (IndexError, ValueError):
            return (0,)

    names.sort(key=lambda n: ("lite" not in n, version(n), n.endswith("latest")), reverse=True)
    return names[:4] + [n for n in names if "lite" in n][:2] or ["gemini-2.5-flash", "gemini-2.5-flash-lite"]


def _contents(messages):
    """Claude formatlı mesajları Gemini «contents»-ə çevirir."""
    names = {}  # tool_use_id -> alətin adı
    out = []
    for m in messages:
        blocks = m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": m["content"]}]
        if m["role"] == "assistant":
            parts = []
            for b in blocks:
                if b.get("type") == "gemini_parts":
                    parts = b["parts"]
                elif b.get("type") == "tool_use":
                    names[b["id"]] = b["name"]
            out.append({"role": "model", "parts": parts or [{"text": ""}]})
            continue
        parts = []
        for b in blocks:
            t = b.get("type")
            if t == "text":
                parts.append({"text": b["text"]})
            elif t == "image":
                parts.append({"inlineData": {"mimeType": b["source"]["media_type"], "data": b["source"]["data"]}})
            elif t == "tool_result":
                try:
                    result = json.loads(b.get("content") or "{}")
                except ValueError:
                    result = b.get("content")
                key = "error" if b.get("is_error") else "result"
                parts.append({"functionResponse": {"name": names.get(b["tool_use_id"], "hesabla"), "response": {key: result}}})
        out.append({"role": "user", "parts": parts})
    return out


def stream(models, messages, tools, emit):
    """Model məşğuldursa və ya limiti dolubsa (cavab başlamamış), növbəti modelə keçir."""
    last = None
    for model in models:
        try:
            return _stream_one(model, messages, tools, emit)
        except GeminiError as e:
            if e.code not in ("overloaded", "rate_limited"):
                raise
            print(f"{model}: {e.code}, növbəti model sınanır", flush=True)
            last = e
    raise GeminiError("rate_limited", str(last))


def _stream_one(model, messages, tools, emit):
    """Gemini-dən axınla cavab alır; mətni emit("text") ilə ötürür, sonda Claude-formatlı nəticə qaytarır."""
    body = {"contents": _contents(messages), "generationConfig": {"maxOutputTokens": 32768}}
    if tools:
        body["tools"] = [{"functionDeclarations": [
            {"name": t["name"], "description": t.get("description", ""), "parameters": t["input_schema"]} for t in tools
        ]}]
    parts, finish, blocked = [], None, None
    try:
        r = _request(f"/v1beta/models/{model}:streamGenerateContent?alt=sse", body)
    except GeminiError:
        raise
    with r:
        for raw in _lines(r, parts):
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            chunk = json.loads(line[5:])
            blocked = (chunk.get("promptFeedback") or {}).get("blockReason") or blocked
            for cand in chunk.get("candidates", [])[:1]:
                for p in (cand.get("content") or {}).get("parts", []):
                    parts.append(p)
                    if "text" in p and not p.get("thought"):
                        emit("text", {"text": p["text"]})
                finish = cand.get("finishReason") or finish

    content = [{"type": "gemini_parts", "parts": parts}]
    text = "".join(p["text"] for p in parts if "text" in p and not p.get("thought"))
    if text:
        content.append({"type": "text", "text": text})
    calls = [p["functionCall"] for p in parts if "functionCall" in p]
    for i, c in enumerate(calls):
        content.append({"type": "tool_use", "id": f"call_{len(messages)}_{i}", "name": c["name"], "input": c.get("args") or {}})

    if blocked or finish in REFUSAL:
        stop = "refusal"
    elif calls:
        stop = "tool_use"
    elif finish == "MAX_TOKENS":
        stop = "max_tokens"
    else:
        stop = "end_turn"
    return {"content": content, "stop_reason": stop}
