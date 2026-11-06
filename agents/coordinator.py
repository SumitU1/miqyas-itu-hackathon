"""Coordinator (the Y.3172 MLFO role in this design): runs a scenario in sequenced chunks.

Per chunk: (1) release each agent ONLY its own facts (plus what it already knew and the coordinator's earlier
rulings sent to it); (2) collect independent structured assessments; (3) the Adviser verifies every citation,
flags conflicts, and answers the policy questions (abstaining unless evidence is strong); (4) write a decision
record, marked needs-human for any data-transfer, clinical or public-claim step, any conflict, abstention or
failure; (5) route a short ruling message to the agents that took part. Approval is never automatic: a record
stays `pending` unless the scenario scripts an approval, which is then logged as `simulated`.
Routed messages carry the action class and the Adviser's wording, never free text written by another agent, so
the Authority cannot learn clinical content from them.
"""
from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from .adviser import Adviser, detect_conflicts
from .agent import RoleAgent
from .roles import AGENT_ROLES

# most protective first
PRIORITY = ("emergency_redirect", "escalate_to_human", "withhold", "notify_authority", "revise_claim",
            "inform_member", "share", "no_action")
HUMAN_CLASSES = ("share", "notify_authority", "revise_claim", "escalate_to_human", "emergency_redirect")
MAX_ADVISER_QUESTIONS = 4


def choose_action(assessments: list[dict]) -> dict:
    live = [a for a in assessments if a.get("status") in ("ok", "emergency", "model_unavailable")]
    if not live:
        return {"class": "no_action", "text": "No agent had anything to assess.", "from": None}
    best = min(live, key=lambda a: PRIORITY.index(a["proposed_action"]["class"]))
    return {**best["proposed_action"], "from": best["agent"]}


class Coordinator:
    def __init__(self, kb, model, audit, plan_queries: bool = False, workers: int = 4):
        self.kb, self.model, self.audit = kb, model, audit
        self.workers = max(1, workers)                      # 1 = one model call at a time
        self.agents = {r: RoleAgent(r, kb, model, audit) for r in AGENT_ROLES}
        self.adviser = Adviser(kb, model, audit, plan_queries=plan_queries)

    # envelope: {msg_id, scenario_id, round, from, to, type, payload, citations, kb_build_id, model_alias}
    def send(self, scenario_id, round_no, frm, to, type_, payload, citations=()):
        env = {"msg_id": uuid.uuid4().hex[:12], "scenario_id": scenario_id, "round": round_no, "from": frm, "to": to,
               "type": type_, "payload": payload, "citations": list(citations), "kb_build_id": self.kb.build_id,
               "model_alias": "auto" if frm.startswith("agent:") else None}
        self.audit.append("message", frm, env)
        return env

    def run_scenario(self, scen: dict) -> list[dict]:
        sid = scen["scenario_id"]
        known = {r: [] for r in AGENT_ROLES}          # cumulative facts per agent
        inbox = {r: [] for r in AGENT_ROLES}          # coordinator messages per agent
        decisions = []
        self.audit.append("scenario_start", "coordinator", {"scenario_id": sid, "title": scen["title"], "chunks": len(scen["chunks"])})
        for n, chunk in enumerate(scen["chunks"], 1):
            decisions.append(self._run_chunk(sid, n, chunk, known, inbox))
        self.audit.append("scenario_end", "coordinator", {"scenario_id": sid, "decisions": [d["decision_id"] for d in decisions]})
        return decisions

    def _run_chunk(self, sid, n, chunk, known, inbox):
        facts = chunk.get("facts", {})
        self.audit.append("chunk_release", "coordinator", {
            "scenario_id": sid, "round": n, "chunk_id": chunk["id"], "title": chunk["title"],
            "release_note": chunk.get("release_note"), "incomplete": chunk.get("incomplete", []),
            "facts_released": {r: facts.get(r, []) for r in AGENT_ROLES}})

        # Model calls are slow and independent, so they run on a thread pool: the three role assessments, and the
        # Adviser's questions (the scripted ones start at once, agents' own open questions as soon as they exist).
        # Everything that is logged as a message is written below, in a fixed order, after the results are in,
        # so a parallel run and a sequential run (workers=1) leave the same message trail and the same decisions.
        participants, jobs = [], []
        for role in AGENT_ROLES:
            known[role].extend(facts.get(role, []))
            if not known[role]:
                continue                                    # this agent has been told nothing yet
            participants.append(role)
            q = chunk["question"]
            q = q.get(role, q.get("default", "")) if isinstance(q, dict) else q
            self.send(sid, n, "coordinator", f"agent:{role}", "release", {"question": q, "new_facts": len(facts.get(role, []))})
            jobs.append((role, q, list(known[role]), list(inbox[role])))

        scripted = list(dict.fromkeys(chunk.get("policy_questions", [])))[:MAX_ADVISER_QUESTIONS]
        ask = lambda q: self.adviser.answer(q, asked_by="coordinator")
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            pending = {q: pool.submit(ask, q) for q in scripted}
            futures = [pool.submit(self.agents[role].assess, sid, n, q, facts_now, messages=msgs,
                                   member_message=chunk.get("member_message") if role == "coach" else None)
                       for role, q, facts_now, msgs in jobs]
            assessments = [f.result() for f in futures]

            verification = self.adviser.verify(assessments)
            conflicts = detect_conflicts(assessments, self.kb.by_id)

            questions = list(chunk.get("policy_questions", []))
            for a in assessments:
                for oq in a["open_questions"][:1]:
                    questions.append(oq)
            questions = list(dict.fromkeys(questions))[:MAX_ADVISER_QUESTIONS]
            for q in questions:
                if q not in pending:
                    pending[q] = pool.submit(ask, q)
            answers = [pending[q].result() for q in questions]

        for role, a in zip(participants, assessments):
            self.send(sid, n, f"agent:{role}", "agent:adviser", "assessment",
                      {k: a[k] for k in ("status", "finding", "proposed_action", "confidence", "open_questions", "citation_violations")},
                      citations=a["provisions"])
        for q, ans in zip(questions, answers):
            self.send(sid, n, "agent:adviser", "coordinator", "ruling" if ans["outcome"] == "ruling" else "abstention",
                      {"question": q, "evidence": ans["evidence"], "outcome": ans["outcome"], "ruling": ans["ruling"],
                       "abstain_reason": ans["abstain_reason"] if "abstain_reason" in ans else None,
                       "binding": ans["binding"], "caveats": ans["caveats"]}, citations=ans["provisions"])

        action = choose_action(assessments)
        reasons = []
        for t in chunk.get("touches", []):
            reasons.append(f"touches {t}")
        if action["class"] in HUMAN_CLASSES:
            reasons.append(f"action '{action['class']}' needs human approval")
        for c in conflicts:
            reasons.append(f"conflict: {c['type']}" + (f" ({c.get('agent')})" if c.get("agent") else ""))
        for ans in answers:
            if ans["outcome"] == "abstain":
                reasons.append(f"adviser abstained ({ans.get('abstain_reason')}): {ans['question'][:80]}")
        for a in assessments:
            if a["citation_violations"]:
                reasons.append(f"citation violations by {a['agent']}: {', '.join(a['citation_violations'])}")
        needs_human = bool(reasons)

        decision = {
            "decision_id": f"{chunk['id']}-D", "scenario_id": sid, "round": n, "chunk_id": chunk["id"],
            "trigger": {"title": chunk["title"], "release_note": chunk.get("release_note"), "incomplete": chunk.get("incomplete", [])},
            "assessments": assessments, "verification": verification, "conflicts": conflicts, "adviser_answers": answers,
            "action": action, "owner": "Miqyas operator" if needs_human else action.get("from"),
            "needs_human": needs_human, "needs_human_reasons": reasons, "approval": {"status": "pending"},
            "kb_build_id": self.kb.build_id,
            "reasoning_trace": {a["agent"]: {"finding": a["finding"], "provisions": a["provisions"], "confidence": a["confidence"]} for a in assessments},
        }
        self.audit.append("decision", "coordinator", decision)

        sa = chunk.get("scripted_approval")
        if sa:
            decision["approval"] = {"status": sa["decision"], "approver": "scripted reviewer (simulated)", "note": sa.get("note", ""), "simulated": True}
            self.audit.append("approval", "human:simulated", {"decision_id": decision["decision_id"], **decision["approval"]})

        summary = f"Decision {decision['decision_id']}: action class '{action['class']}', needs human: {needs_human}. " + " ".join(
            (f"Adviser ruling: {x['ruling']}" if x["outcome"] == "ruling" else f"Adviser abstained ({x.get('abstain_reason')}) on: {x['question'][:80]}") for x in answers)
        for role in participants:
            msg = self.send(sid, n, "coordinator", f"agent:{role}", "ruling", {"text": summary}, citations=[p for x in answers for p in x["provisions"]])
            inbox[role].append({"from": "coordinator", "type": "ruling", "text": summary})
        return decision
