"""Policy & Legal Adviser (the Y.3172 "P" node in this design).

It reads the whole KB and does three jobs:
  answer(question)      a ruling ONLY when the evidence gate says "strong"; otherwise it abstains, without
                        calling the model, and hands the best passages to a human. A ruling whose citations are
                        not among the passages retrieved is discarded.
  verify(assessments)   checks every citation an agent made: the chunk exists, how well it fits the agent's own
                        finding (rank under the same BM25 search), page and link, and caveats read from the
                        chunk record (not from the model): revision date passed, summary only, non-binding ...
  detect_conflicts      share-versus-withhold between agents, citations spread over Dubai / Abu Dhabi / federal,
                        and agents that gave no usable assessment.
Nothing here is legal advice and no lawyer has reviewed it.
"""
from __future__ import annotations

from .agent import _passage
from .llm import as_list, extract_json

BINDING_KINDS = ("law", "regulation")
JURISDICTIONS = ("federal", "dubai", "abu-dhabi")

SYSTEM = """You are the Policy & Legal Adviser in a multi-agent system working with UAE health-policy documents. You are not a lawyer and this is not legal advice; nobody qualified has reviewed this knowledge base.
Answer the QUESTION using ONLY the PASSAGES supplied. Word the answer as "the text says ...". Cite only chunk ids from the PASSAGES; decision ids such as S3-C1-D, which may appear in a question or in other agents' messages, are not chunk ids and must never be cited. Never rely on memory for any article, number or fine.
A document marked as a summary, guidance or non-binding is not the binding text: say so. Say what the passages do NOT settle.
Reply with ONE JSON object only: {"ruling": "<3-6 sentences>", "provisions": ["<chunk id>", ...], "conditions": ["<what must be true or checked before relying on this>"]}"""


def chunk_caveats(c: dict) -> list[str]:
    vs = (c.get("version_status") or "")
    low = vs.lower()
    out = []
    if "PASSED" in vs:
        out.append("revision-date-passed")
    if "summary" in low:
        out.append("summary-only")
    if "non-binding" in low:
        out.append("non-binding")
    if "superseded" in low or "predate" in low:
        out.append("may-be-superseded")
    if "not confirmed" in low or "check currency" in low or "check for a newer" in low:
        out.append("currency-unconfirmed")
    if c.get("capture_note") and "NOT in this file" in c["capture_note"]:
        out.append("partial-capture")
    if c.get("clinical_review") == "clinical-unreviewed":
        out.append("clinical-unreviewed")
    return out


def detect_conflicts(assessments: list[dict], by_id: dict) -> list[dict]:
    flags = []
    usable = [a for a in assessments if a.get("status") == "ok"]
    for a in assessments:
        if a.get("status") not in ("ok", "emergency"):
            flags.append({"type": "missing-assessment", "agent": a["agent"], "detail": "no usable assessment from this agent"})
    classes = {a["agent"]: a["proposed_action"]["class"] for a in usable}
    if "share" in classes.values() and "withhold" in classes.values():
        flags.append({"type": "action-conflict", "detail": "agents propose opposite actions", "actions": classes})
    juris = {by_id[p]["jurisdiction"] for a in usable for p in a.get("provisions", []) if p in by_id}
    juris &= set(JURISDICTIONS)
    # federal law sitting beside one emirate's rules is normal layering; two emirates' rules is a real question
    if {"dubai", "abu-dhabi"} <= juris:
        flags.append({"type": "jurisdiction-spread", "jurisdictions": sorted(juris),
                      "detail": "cited provisions come from both Dubai and Abu Dhabi: which applies must be settled by a human"})
    return flags


EVIDENCE_ORDER = {"none": 0, "weak": 1, "strong": 2}

PLAN_SYSTEM = """You turn a question about UAE health-policy rules into short keyword search queries for a search over the text of laws, regulations, policies and standards. Use the vocabulary those texts use (for example: controller, data subject, facility, patient, consent, advertisement, licence, approval, transfer, outside the State). Give at most 3 queries of 4 to 12 words each. Do not answer the question.
Reply with ONE JSON object only: {"queries": ["...", "..."]}"""


class Adviser:
    name = "adviser"
    actor = "agent:adviser"

    def __init__(self, kb, model, audit, plan_queries: bool = False):
        self.kb, self.model, self.audit = kb, model, audit
        self.plan_queries = plan_queries

    def _plan(self, question: str) -> list[str]:
        r = self.model.complete(self.actor, PLAN_SYSTEM, f"QUESTION: {question}")
        parsed = extract_json(r["text"]) if r["ok"] else None
        return [q[:160] for q in as_list((parsed or {}).get("queries"))][:3]

    def answer(self, question: str, asked_by: str) -> dict:
        """Planned queries can only ADD candidates: the raw question is always tried, and the best evidence level wins.
        Every query is in the audit log. The evidence level therefore describes the query that was used (`query_used`)."""
        candidates = list(dict.fromkeys([question] + (self._plan(question) if self.plan_queries else [])))
        tried, best, best_key = [], None, None
        for q in candidates:
            res = self.kb.query(self.actor, q, k=5)
            top = res["results"][0]["score"] if res["results"] else 0.0
            tried.append({"query": q, "evidence": res["evidence"], "top_score": top})
            key = (EVIDENCE_ORDER[res["evidence"]], top)
            if best is None or key > best_key:
                best, best_key = (q, res), key
        used, res = best
        ev, chunks = res["evidence"], res["results"]
        ids = [c["chunk_id"] for c in chunks]
        base = {"question": question, "asked_by": asked_by, "evidence": ev, "retrieved": ids, "query_used": used,
                "queries_tried": tried, "rejected_citations": []}
        if ev != "strong":
            return {**base, "outcome": "abstain", "abstain_reason": f"evidence-{ev}", "ruling": None, "provisions": [],
                    "binding": False, "caveats": [],
                    "for_human": [{"chunk_id": c["chunk_id"], "citation": c["citation"], "url": c["url"], "score": c["score"]} for c in chunks[:3]]}
        user = f"QUESTION (from {asked_by}): {question}\n\nPASSAGES:\n" + "\n\n".join(_passage(c) for c in chunks)
        reason, rejected = None, []
        for attempt in range(2):
            u = user if attempt == 0 else (user + f"\n\nYour previous reply was rejected ({reason}). Reply with the JSON object only. "
                                           f"Cite only these chunk ids: {', '.join(ids)}.")
            r = self.model.complete(self.actor, SYSTEM, u)
            if not r["ok"]:
                reason = reason or "model-unavailable"
                continue
            parsed = extract_json(r["text"])
            if not parsed or not isinstance(parsed.get("ruling"), str) or not parsed["ruling"].strip():
                reason = "unparseable-reply"
                continue
            cited = as_list(parsed.get("provisions"), split=True)
            valid = [p for p in dict.fromkeys(cited) if p in ids]
            bad = [p for p in dict.fromkeys(cited) if p not in ids]
            if not valid or bad:
                rejected += [b for b in bad if b not in rejected]
                reason = "citation-check-failed"
                continue
            return {**self._finish(valid, str(parsed["ruling"])[:1500], [x[:300] for x in as_list(parsed.get("conditions"))][:4],
                                   retrieved=ids, evidence=ev, question=question, asked_by=asked_by),
                    "query_used": used, "queries_tried": tried, "rejected_citations": rejected}
        return {**base, "outcome": "abstain", "abstain_reason": reason, "ruling": None, "provisions": [], "binding": False,
                "caveats": [], "for_human": [], "rejected_citations": rejected}

    def _finish(self, provisions, ruling, conditions, retrieved, evidence, question, asked_by) -> dict:
        cs = [self.kb.get(p) for p in provisions]
        binding = all(c["kind"] in BINDING_KINDS and "summary" not in (c["version_status"] or "").lower() for c in cs)
        caveats = sorted({cv for c in cs for cv in chunk_caveats(c)})
        if not binding:
            ruling += " (Note added by the system: the cited documents are guidance, standards or summaries, not binding law.)"
        return {"question": question, "asked_by": asked_by, "evidence": evidence, "retrieved": retrieved, "outcome": "ruling",
                "abstain_reason": None, "ruling": ruling, "provisions": provisions, "conditions": conditions,
                "binding": binding, "caveats": caveats, "for_human": []}

    def verify(self, assessments: list[dict]) -> list[dict]:
        out = []
        for a in assessments:
            rows = []
            for cid in a.get("provisions", []):
                c = self.kb.get(cid)
                if c is None:
                    rows.append({"chunk_id": cid, "exists": False, "support": "does-not-exist", "caveats": []})
                    continue
                rank = self.kb.rank_of(a.get("finding", ""), cid, top=25)
                support = "supported" if rank and rank <= 10 else "loosely-supported" if rank else "not-supported-by-finding-text"
                rows.append({"chunk_id": cid, "exists": True, "rank": rank, "support": support, "citation": c["citation"],
                             "locator": c["locator"], "url": c["url"], "section": c["section"], "jurisdiction": c["jurisdiction"],
                             "caveats": chunk_caveats(c)})
            out.append({"agent": a["agent"], "citations": rows, "citation_violations": a.get("citation_violations", [])})
        self.audit.append("verification", self.actor, {"rows": out})
        return out
