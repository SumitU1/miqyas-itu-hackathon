"""KB access for agents: scoped search that writes every query to the audit log."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "kb"))

import search as kbsearch  # noqa: E402


def load_kb(public: bool = False):
    if public or kbsearch.FULL.exists():
        return kbsearch.KB(kbsearch.PUBLIC if public else kbsearch.FULL)
    if not kbsearch.PUBLIC.exists():
        raise FileNotFoundError(
            "No knowledge base found. Run scripts/fetch_sources.py, then kb/build_kb.py."
        )
    print(
        "kb/out/chunks.jsonl is not here (full text is not redistributed), so this run uses the "
        "60-word public excerpts. Retrieval scores differ from the published runs. Rebuild the "
        "full text with scripts/fetch_sources.py, then kb/build_kb.py.",
        file=sys.stderr,
    )
    return kbsearch.KB(kbsearch.PUBLIC)


class KBTool:
    def __init__(self, kb, audit):
        self.kb = kb
        self.audit = audit
        self.by_id = {c["chunk_id"]: c for c in kb.chunks}
        self.build_id = kb.chunks[0]["build_id"]

    def query(self, actor: str, text: str, scope=None, k: int = 5) -> dict:
        res = self.kb.search(text, k=k, source=set(scope) if scope else None)
        ev = kbsearch.evidence_level(res)
        self.audit.kb_query(actor, text, [c["chunk_id"] for c in res], [c["score"] for c in res], ev, self.build_id,
                            filters={"scope": sorted(scope) if scope else None, "k": k})
        return {"evidence": ev, "results": res}

    def get(self, chunk_id: str):
        return self.by_id.get(chunk_id)

    def rank_of(self, text: str, chunk_id: str, top: int = 20):
        """1-based rank of chunk_id for this wording over the WHOLE KB, or None if outside the top `top`."""
        for i, c in enumerate(self.kb.search(text, k=top), 1):
            if c["chunk_id"] == chunk_id:
                return i
        return None
