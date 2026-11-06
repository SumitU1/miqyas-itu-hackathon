"""Model access through an OpenAI-compatible gateway, alias `auto` only.

`auto` is the free pool (K2 first). No paid model is named anywhere in this repo, and no Anthropic key is
read. The gateway key comes from the GATEWAY_LLM_KEY environment variable or from a .env file named in
GATEWAY_ENV_FILE; it is sent only as the Authorization header and is never written to the audit log,
an error message or stdout. The audit log records the alias, the model the gateway says answered and a
hash of the prompt (not the prompt text).
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from .audit import sha256_text

DEFAULT_URL = "http://127.0.0.1:3001/v1"
ALIAS = "auto"


def load_key(env: dict) -> str:
    if env.get("GATEWAY_LLM_KEY"):
        return env["GATEWAY_LLM_KEY"]
    f = env.get("GATEWAY_ENV_FILE")
    if f and Path(f).exists():
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            if line.startswith("GATEWAY_LLM_KEY="):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                if v:
                    return v
    raise RuntimeError("no gateway key: set GATEWAY_LLM_KEY, or GATEWAY_ENV_FILE pointing at a .env that holds it")


def as_list(value, split: bool = False) -> list[str]:
    """Models sometimes send "a, b" or "a" where a list was asked for; iterating that string would
    treat every character as an item. Lists pass through, a string becomes one item (or is split on
    commas, semicolons and newlines when `split`), anything else that is not a number becomes []."""
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [str(value)]
    if isinstance(value, str):
        parts = re.split(r"[,;\n]+", value) if split else [value]
        return [p.strip() for p in parts if p.strip()]
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if isinstance(v, (str, int, float)) and not isinstance(v, bool)]
    return []


def extract_json(text: str):
    """First JSON object in a model reply (handles code fences, prose around it and <think> blocks)."""
    if not text:
        return None
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    dec = json.JSONDecoder()
    i = text.find("{")
    while i != -1:
        try:
            obj, _ = dec.raw_decode(text[i:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        i = text.find("{", i + 1)
    return None


def _urllib_transport(url, headers, body, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            status = r.status
    except urllib.error.HTTPError as e:
        raw, status = e.read().decode("utf-8", "replace"), e.code
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


class ModelClient:
    def __init__(self, base_url, key, audit, transport=None, retries=2, backoff=3.0, timeout=180,
                 max_tokens=3500, temperature=0.2):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self._key = key
        self.audit = audit
        self.transport = transport or _urllib_transport
        self.retries, self.backoff, self.timeout = retries, backoff, timeout
        self.max_tokens, self.temperature = max_tokens, temperature
        self.calls = 0
        self._lock = threading.Lock()                      # agents call from several threads

    def _redact(self, s) -> str:
        return str(s).replace(self._key, "[redacted]")[:300]

    def complete(self, actor: str, system: str, user: str) -> dict:
        body = {"model": ALIAS, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": self.temperature, "max_tokens": self.max_tokens}
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        phash = sha256_text(system + "\n---\n" + user)
        error, served = None, None
        for attempt in range(self.retries + 1):
            with self._lock:
                self.calls += 1
            try:
                status, data = self.transport(self.url, headers, body, self.timeout)
            except Exception as e:  # network errors are data here, not crashes
                status, data = None, None
                error = self._redact(e)
            else:
                if status == 200 and isinstance(data, dict):
                    served = data.get("model")
                    try:
                        content = data["choices"][0]["message"]["content"]
                    except (KeyError, IndexError, TypeError):
                        content = None
                    text = content.strip() if isinstance(content, str) else ""    # list/int/dict content = empty reply
                    if text:
                        self.audit.model_call(actor, ALIAS, phash, ok=True, served_model=served)
                        return {"ok": True, "text": text, "served_model": served, "prompt_hash": phash, "error": None}
                    error = "empty reply"
                else:
                    error = self._redact(f"HTTP {status}: {data if isinstance(data, str) else json.dumps(data)[:200]}")
            if attempt < self.retries:
                time.sleep(self.backoff)
        self.audit.model_call(actor, ALIAS, phash, ok=False, served_model=served, error=error)
        return {"ok": False, "text": "", "served_model": served, "prompt_hash": phash, "error": error}
