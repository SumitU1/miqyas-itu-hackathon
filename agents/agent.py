"""Role agents (Miqyas Coach, Partner Clinic, Health-Data Authority).

One class, three mandates. Each agent:
  1. retrieves ONLY from the KB sources in its mandate (every query is audited);
  2. asks the model for a structured assessment, shown only its own facts, the coordinator's messages and the
     retrieved passages (with each document's status caveat);
  3. has its citations checked mechanically: an id that was not among the passages it was shown is stripped,
     recorded as a citation violation, and lowers confidence. The model's stated rationale plus its cited ids
     is the reasoning trace; hidden model reasoning is neither requested nor stored.
"""
from __future__ import annotations

import re

from .guard import input_guard, output_guard
from .llm import as_list, extract_json
from .roles import ROLES

ACTION_CLASSES = ("no_action", "inform_member", "share", "withhold", "notify_authority", "revise_claim",
                  "escalate_to_human", "emergency_redirect")
CONFIDENCE = ("low", "medium", "high")
PASSAGE_WORDS = 200

SYSTEM = """You are the {title} in a multi-agent system that must act inside the written rules of the UAE health-policy documents. Your institutional role: {brief_role}. You see {sees}.
You must not: {must_not}.
Rules of work:
- Ground every legal or policy statement in the PASSAGES supplied. Cite only chunk ids that appear in the PASSAGES list. Never state a law, article or number from memory. If the passages do not settle the point, say so in open_questions and set confidence to low.
- Word claims as "the text says ...". You are not a lawyer and nothing here is legal advice. Treat any document whose status note says it may be out of date or is only a summary as non-binding evidence and say so.
- Never give a diagnosis or a dose. Clinical content is unreviewed.
- Other agents hold different information. Do not guess what they know.
Reply with ONE JSON object and nothing else:
{{"finding": "<2-4 sentences: what the situation is under the passages>",
 "provisions": ["<chunk id>", ...],
 "proposed_action": {{"class": "<one of {classes}>", "text": "<one sentence>"}},
 "confidence": "low|medium|high",
 "open_questions": ["<question for the policy adviser, if the passages do not settle it>"]{extra}}}"""

COACH_EXTRA = ', "draft_reply_to_member": "<short plain reply to the member, or empty>"'


def _passage(c: dict) -> str:
    words = re.sub(r"\s+", " ", c["text"]).split()
    body = " ".join(words[:PASSAGE_WORDS]) + (" ..." if len(words) > PASSAGE_WORDS else "")
    cap = f" | capture note: {c['capture_note'][:160]}" if c.get("capture_note") else ""
    return (f"[{c['chunk_id']}] {c['title']} | {c['section']} | {c['locator']} | {c['jurisdiction']} | "
            f"status: {c['version_status']}{cap}\n{body}")


class RoleAgent:
    def __init__(self, role: str, kb, model, audit):
        self.role = ROLES[role]
        self.name = role
        self.kb, self.model, self.audit = kb, model, audit
        self.actor = f"agent:{role}"

    def retrieve(self, question: str, facts: list[str]) -> list[dict]:
        seen, out = set(), []
        queries = [question] + ([" ".join(facts[0].split()[:40])] if facts else [])
        for q in queries:
            for c in self.kb.query(self.actor, q, scope=self.role.scope, k=4)["results"]:
                if c["chunk_id"] not in seen and len(out) < 6:
                    seen.add(c["chunk_id"])
                    out.append(c)
        return out

    def _base(self, status, finding, cls, text, retrieved=(), confidence="low"):
        return {"agent": self.name, "status": status, "finding": finding, "provisions": [],
                "proposed_action": {"class": cls, "text": text}, "confidence": confidence, "open_questions": [],
                "citation_violations": [], "retrieved": list(retrieved), "draft_reply_to_member": None,
                "guard": {"violations": []}}

    def assess(self, scenario_id: str, round_no: int, question: str, facts: list[str], messages=(), member_message=None) -> dict:
        if self.name == "coach" and member_message:
            g = input_guard(member_message)
            if g["action"] == "emergency":
                out = self._base("emergency", "The member's message contains emergency language; the model was not called.",
                                 "emergency_redirect", "Send the emergency message and stop the chat flow.", confidence="high")
                out["draft_reply_to_member"] = g["reply"]
                self.audit.append("guard", self.actor, {"input": "emergency", "scenario_id": scenario_id, "round": round_no})
                return out

        passages = self.retrieve(question, facts)
        ids = [c["chunk_id"] for c in passages]
        system = SYSTEM.format(title=self.role.title, brief_role=self.role.brief_role, sees=self.role.sees,
                               must_not="; ".join(self.role.must_not), classes=" | ".join(ACTION_CLASSES),
                               extra=COACH_EXTRA if self.name == "coach" else "")
        user = (f"SCENARIO {scenario_id}, round {round_no}\nQUESTION FOR YOU: {question}\n\nFACTS YOU HOLD:\n"
                + "\n".join(f"- {f}" for f in facts)
                + ("\n\nMESSAGES ROUTED TO YOU:\n" + "\n".join(f"- from {m['from']} ({m['type']}): {m['text']}" for m in messages) if messages else "")
                + (f"\n\nMEMBER'S MESSAGE (synthetic): {member_message}" if member_message else "")
                + "\n\nPASSAGES (your only allowed sources):\n" + ("\n\n".join(_passage(c) for c in passages) or "(none found)"))

        parsed, err = None, None
        for attempt in range(2):
            r = self.model.complete(self.actor, system, user if attempt == 0 else user + "\n\nYour previous reply was not a valid JSON object. Reply with the JSON object only.")
            if not r["ok"]:
                err = r["error"]
                continue
            parsed = extract_json(r["text"])
            if parsed is not None and isinstance(parsed.get("finding"), str) and parsed["finding"].strip():
                break
            parsed, err = None, "unparseable reply" if parsed is None else "reply has no usable finding"
        if parsed is None:
            out = self._base("model_unavailable", f"No usable model answer ({err}).", "escalate_to_human",
                             "A human must assess this step.", retrieved=ids)
            self.audit.append("assessment_failed", self.actor, {"scenario_id": scenario_id, "round": round_no, "error": err})
            return out

        out = self._base("ok", parsed["finding"][:1200], "escalate_to_human", "", retrieved=ids)
        pa = parsed.get("proposed_action")
        if isinstance(pa, str):
            pa = {"class": "escalate_to_human", "text": pa}
        pa = pa if isinstance(pa, dict) else {}
        cls = pa.get("class") if pa.get("class") in ACTION_CLASSES else "escalate_to_human"
        out["proposed_action"] = {"class": cls, "text": str(pa.get("text", ""))[:400]}
        conf = parsed.get("confidence")
        out["confidence"] = conf if conf in CONFIDENCE else "low"
        cited = as_list(parsed.get("provisions"), split=True)
        out["provisions"] = [p for p in dict.fromkeys(cited) if p in ids]
        out["citation_violations"] = [p for p in dict.fromkeys(cited) if p not in ids]
        if out["citation_violations"] or (not out["provisions"] and cls not in ("no_action", "escalate_to_human", "inform_member")):
            out["confidence"] = "low"
        out["open_questions"] = [q[:300] for q in as_list(parsed.get("open_questions"))][:3]
        if self.name == "coach":
            reply = parsed.get("draft_reply_to_member")
            if not isinstance(reply, str):                  # list of strings -> joined; number -> text; dict/bool/None -> no draft
                reply = " ".join(as_list(reply))
            if reply:
                g = output_guard(reply)
                out["draft_reply_to_member"] = g["text"]
                out["guard"] = {"violations": g["violations"]}
                if g["violations"]:
                    self.audit.append("guard", self.actor, {"output": g["violations"], "excerpts": g["excerpts"],
                                                            "scenario_id": scenario_id, "round": round_no})
        return out
