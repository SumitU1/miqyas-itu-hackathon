"""Append-only, hash-chained audit log (one JSONL file per run).

Each record stores the SHA-256 of the previous record, so an edited, deleted or reordered line breaks
the chain at a known place. A chain alone cannot see lines cut off the END of the file: publish
`head_hash` (for example in the report) and pass it to `verify_file(expected_head=...)` for that.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path

GENESIS = "0" * 64
_FIELDS = ("seq", "run_id", "ts", "type", "actor", "payload", "prev_hash")


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def record_hash(rec: dict) -> str:
    return hashlib.sha256(_canonical({k: rec[k] for k in _FIELDS})).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _raw_lines(path) -> list[bytes]:
    # Line ends are \n, \r\n or a lone \r (what read_text's universal newlines already treated as one) and
    # nothing else. str.splitlines() also splits on U+2028, U+2029, U+0085, VT, FF and FS/GS/RS; json.dumps
    # (ensure_ascii=False) leaves the first three raw inside strings, so splitlines() would cut a record in two.
    # Splitting the bytes is safe: 0x0A and 0x0D never occur inside a multi-byte UTF-8 sequence.
    return Path(path).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n").split(b"\n")


def read_log_lines(path) -> list[str]:
    """The lines of a JSONL audit log, split on real line ends only (see `_raw_lines`)."""
    return [b.decode("utf-8") for b in _raw_lines(path)]


def verify_file(path, expected_head: str | None = None):
    """Return (ok, info). info has `records` when ok, else `bad_seq` and `reason`. Bad content never raises."""
    path = Path(path)
    prev, n = GENESIS, 0
    if path.exists():
        for raw in _raw_lines(path):
            try:
                line = raw.decode("utf-8")
            except UnicodeDecodeError:
                return False, {"bad_seq": n, "reason": "line is not valid UTF-8"}
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                return False, {"bad_seq": n, "reason": "line is not valid JSON"}
            if not isinstance(rec, dict):
                return False, {"bad_seq": n, "reason": f"line is not a JSON object (found {type(rec).__name__})"}
            if rec.get("seq") != n:
                return False, {"bad_seq": n, "reason": f"sequence gap: expected {n}, found {rec.get('seq')}"}
            if rec.get("prev_hash") != prev:
                return False, {"bad_seq": n, "reason": "prev_hash does not match the previous record's hash"}
            missing = [k for k in _FIELDS if k not in rec]
            if missing:
                return False, {"bad_seq": n, "reason": f"record is missing field(s): {', '.join(missing)}"}
            if record_hash(rec) != rec.get("hash"):
                return False, {"bad_seq": n, "reason": "record hash does not match its content"}
            prev, n = rec["hash"], n + 1
    if expected_head is not None and prev != expected_head:
        return False, {"bad_seq": n, "reason": "head hash differs from the published head (records missing at the end)"}
    return True, {"records": n, "head": prev}


class AuditLog:
    def __init__(self, path, run_id: str):
        self.path = Path(path)
        self.run_id = run_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()                      # agents may append from several threads
        ok, info = verify_file(self.path)
        if not ok:
            raise ValueError(f"audit log {self.path} fails verification, refusing to append: {info}")
        self.seq = info["records"] if ok else 0
        self.head_hash = info["head"]

    def append(self, type_: str, actor: str, payload: dict) -> dict:
        with self._lock:                                    # seq, prev_hash and the file write must be one step
            rec = {"seq": self.seq, "run_id": self.run_id, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "type": type_, "actor": actor, "payload": payload, "prev_hash": self.head_hash}
            rec["hash"] = record_hash(rec)
            with self.path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.seq += 1
            self.head_hash = rec["hash"]
            return rec

    # typed helpers: the fields the brief asks to be reviewable
    def kb_query(self, actor, query, chunk_ids, scores, evidence, kb_build_id, filters=None):
        return self.append("kb_query", actor, {"query": query, "chunk_ids": chunk_ids, "scores": scores,
                                               "evidence": evidence, "kb_build_id": kb_build_id, "filters": filters or {}})

    def model_call(self, actor, model_alias, prompt_hash, ok, served_model=None, error=None):
        return self.append("model_call", actor, {"model_alias": model_alias, "served_model": served_model,
                                                 "prompt_hash": prompt_hash, "ok": ok, "error": error})
