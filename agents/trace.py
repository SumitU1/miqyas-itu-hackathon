"""Rebuild "why was this decided" from an audit log: trigger -> assessments -> cited chunks (page, link) -> ruling -> approval.

The reasoning trace shown here is each agent's STATED rationale (the `finding`) plus its cited chunk ids. Hidden model
reasoning is neither requested nor stored. The chain is verified first; if it fails, the output says so at the top.
"""
from __future__ import annotations

import json
from pathlib import Path

from .audit import read_log_lines, verify_file


def _cite_line(c: dict) -> str:
    if not c.get("exists", True):
        return f"  - `{c['chunk_id']}` DOES NOT EXIST"
    cav = f" caveats: {', '.join(c['caveats'])}" if c.get("caveats") else ""
    return (f"  - `{c['chunk_id']}` {c['citation']} ({c['section']}; {c['locator']}) "
            f"{c['url']} | fit to finding: {c['support']}{cav}")


def build_trace(log_path, kb) -> str:
    log_path = Path(log_path)
    ok, info = verify_file(log_path)
    recs = [json.loads(l) for l in read_log_lines(log_path) if l.strip()]
    out = ["# Decision trace", ""]
    out.append(f"Audit chain: **chain verified** ({info['records']} records, head `{info['head'][:16]}...`)" if ok
               else f"Audit chain: **FAILS verification** at record {info['bad_seq']}: {info['reason']}. Treat everything below as untrusted.")
    out += ["", "The reasoning trace is each agent's *stated rationale* plus the chunk ids it cited; hidden model reasoning is not requested or stored. "
            "Nothing here is legal advice and no lawyer or clinician has reviewed the knowledge base.", ""]
    approvals = {r["payload"]["decision_id"]: r["payload"] for r in recs if r["type"] == "approval"}
    for r in recs:
        if r["type"] != "decision":
            continue
        d = r["payload"]
        out.append(f"## {d['decision_id']}: {d['trigger']['title']}")
        if d["trigger"].get("release_note"):
            out.append(f"Trigger: {d['trigger']['release_note']}")
        if d["trigger"].get("incomplete"):
            out.append("Information missing at this step: " + "; ".join(d["trigger"]["incomplete"]))
        out.append("")
        ver = {v["agent"]: v for v in d["verification"]}
        for a in d["assessments"]:
            out.append(f"**{a['agent']}** [{a['status']}, confidence {a['confidence']}] proposes `{a['proposed_action']['class']}`: {a['finding']}")
            for c in ver.get(a["agent"], {}).get("citations", []):
                out.append(_cite_line(c))
            if a["citation_violations"]:
                out.append(f"  - citation violations (stripped): {', '.join(a['citation_violations'])}")
            if a.get("draft_reply_to_member"):
                g = a.get("guard", {}).get("violations", [])
                out.append(f"  - draft reply to the member (after the safety guard{', which blocked: ' + ', '.join(g) if g else ''}): {a['draft_reply_to_member']}")
            out.append("")
        if d["conflicts"]:
            out.append("Conflicts flagged by the Adviser: " + "; ".join(f"{c['type']}" + (f" ({', '.join(c['jurisdictions'])})" if c.get("jurisdictions") else "") for c in d["conflicts"]))
            out.append("")
        for x in d["adviser_answers"]:
            qu = f" [query used: \"{x['query_used']}\"; {len(x['queries_tried'])} tried]" if x.get("query_used") else ""
            rej = f" Rejected citations: {', '.join(x['rejected_citations'])}." if x.get("rejected_citations") else ""
            if x["outcome"] == "ruling":
                out.append(f"Adviser, evidence {x['evidence']}, binding text: {x['binding']}: *{x['question']}*{qu} -> {x['ruling']} (cites {', '.join(x['provisions'])}; caveats: {', '.join(x['caveats']) or 'none'}){rej}")
            else:
                out.append(f"Adviser **abstained** ({x['abstain_reason']}, evidence {x['evidence']}): *{x['question']}*{qu}{rej}")
        out.append("")
        out.append(f"**Action:** `{d['action']['class']}` (from {d['action'].get('from')}). Needs human: **{d['needs_human']}**" + (": " + "; ".join(d["needs_human_reasons"]) if d["needs_human_reasons"] else ""))
        ap = approvals.get(d["decision_id"], d["approval"])
        out.append(f"**Approval:** {ap['status']}" + (f" by {ap['approver']}" + (" (simulated)" if ap.get("simulated") else "") + (f": {ap.get('note')}" if ap.get("note") else "") if ap["status"] != "pending" else " (no human has decided)"))
        out.append("")
    return "\n".join(out)
