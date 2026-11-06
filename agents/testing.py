"""Test doubles. ScriptedModel stands in for the gateway in unit tests: no network, fully deterministic."""
from __future__ import annotations

import json
import threading
import time


class ScriptedModel:
    """Replies come from `script`: a list (popped in order) or a function (actor, system, user) -> text | None.
    None means a failed call. Every prompt is kept in `.prompts` so tests can check what an agent was shown.
    `latency` (seconds) makes each call sleep first, to stand in for a slow gateway. Safe to call from threads."""

    def __init__(self, script, latency: float = 0.0):
        self.script = script
        self.latency = latency
        self.prompts = []
        self.calls = 0
        self._lock = threading.Lock()

    def complete(self, actor, system, user):
        if self.latency:
            time.sleep(self.latency)
        with self._lock:
            self.calls += 1
            self.prompts.append({"actor": actor, "system": system, "user": user})
            fn = self.script
        out = fn(actor, system, user) if callable(fn) else self._pop()
        if out is None:
            return {"ok": False, "text": "", "served_model": None, "prompt_hash": "x", "error": "scripted failure"}
        if not isinstance(out, str):
            out = json.dumps(out)
        return {"ok": True, "text": out, "served_model": "scripted", "prompt_hash": "x", "error": None}

    def _pop(self):
        with self._lock:
            return self.script.pop(0) if self.script else None


def assessment_json(finding="f", provisions=(), cls="escalate_to_human", text="t", confidence="medium", open_questions=(), draft_reply=None):
    d = {"finding": finding, "provisions": list(provisions), "proposed_action": {"class": cls, "text": text},
         "confidence": confidence, "open_questions": list(open_questions)}
    if draft_reply is not None:
        d["draft_reply_to_member"] = draft_reply
    return d
