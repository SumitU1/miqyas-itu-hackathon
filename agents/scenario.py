"""Scenario files: load and validate. Synthetic data only (checked for identifier-like strings)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .roles import AGENT_ROLES

SAFE_ID = re.compile(r"[A-Za-z0-9_-]{1,40}")
IDENTIFIER = re.compile(r"\b784-?\d{4}-?\d{7}-?\d\b|[\w.+-]+@[\w-]+\.[\w.]+|\+?971[\s-]?\d{1,2}[\s-]?\d{3}[\s-]?\d{4}")


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def validate_scenario(s: dict) -> list[str]:
    errs = []
    if s.get("synthetic") is not True:
        errs.append("scenario must declare synthetic: true")
    for k in ("scenario_id", "title", "member", "chunks"):
        if k not in s:
            errs.append(f"missing {k}")
    sid = s.get("scenario_id")
    if "scenario_id" in s and not (isinstance(sid, str) and SAFE_ID.fullmatch(sid)):
        errs.append("scenario_id must be 1-40 letters, digits, '-' or '_' (it becomes a folder name)")
    seen = set()
    for c in s.get("chunks", []):
        for k in ("id", "title", "question", "facts"):
            if k not in c:
                errs.append(f"chunk {c.get('id', '?')} missing {k}")
        if c.get("id") in seen:
            errs.append(f"duplicate chunk id {c['id']}")
        seen.add(c.get("id"))
        cid = c.get("id")
        facts = c.get("facts", {})
        for r, fl in (facts.items() if isinstance(facts, dict) else []):
            if r not in AGENT_ROLES:
                errs.append(f"chunk {cid}: facts for unknown role '{r}'")
            elif not isinstance(fl, list) or not all(isinstance(x, str) for x in fl):
                errs.append(f"chunk {cid}: facts for '{r}' must be a list of strings")   # a bare string would be read letter by letter
            elif any(not x.strip() for x in fl):
                errs.append(f"chunk {cid}: facts for '{r}' contain an empty string")
        q = c.get("question")
        if isinstance(q, dict):
            missing = [r for r in AGENT_ROLES if not str(q.get(r, q.get("default", ""))).strip()]
            if missing:
                errs.append(f"chunk {cid}: question has no text for {', '.join(missing)} (add a 'default' or one per role)")
        elif "question" in c and not (isinstance(q, str) and q.strip()):
            errs.append(f"chunk {cid}: question is blank")
        pq = c.get("policy_questions", [])
        if not isinstance(pq, list) or not all(isinstance(x, str) and x.strip() for x in pq):
            errs.append(f"chunk {cid}: policy_questions must be a list of non-empty strings")
    for t in _strings(s):
        if IDENTIFIER.search(t):
            errs.append(f"identifier-like string (ID, email or phone) in scenario: {t[:40]}")
            break
    return errs


def load_scenarios(folder) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(folder).glob("S*.json"))]
