"""Generate docs/SOURCE_LIST.md from sources/sources.json (so the list can never drift from the registry)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
reg = json.loads((ROOT / "sources" / "sources.json").read_text(encoding="utf-8"))
cov = {r["id"]: r for r in json.loads((ROOT / "kb" / "out" / "coverage.json").read_text(encoding="utf-8"))["rows"]}
S = reg["sources"]

order = {"federal": 0, "dubai": 1, "abu-dhabi": 2, "international": 3}
S_sorted = sorted(S, key=lambda s: (order.get(s["jurisdiction"], 9), s["kind"], s["id"]))

L = [
    "# Source list: public UAE health-policy documents for the Miqyas KB (v0.1)",
    "",
    "Generated from `sources/sources.json` on 2026-10-26. **Public documents only.** The files behind every row marked 'In KB' were downloaded or captured on 2026-10-26. URLs in rows marked NO were taken from search results and could not be opened by this project (bot protection), so treat them as unverified until a person opens them.",
    "",
    "How to read the columns: **Level** = federal / emirate / international. **Status** is what the document itself says about its version, plus a note when the stated revision date has already passed. **Reuse** is the licence position found: none of the UAE documents states an open licence, so the public export ships only a short excerpt per chunk with a link to the original. **In KB** = ingested into KB v1.",
    "",
    "> Not legal advice. Nothing in this list or in the KB has been reviewed by a UAE lawyer.",
    "",
    "| # | ID | Document | Issuer | Level | Date | Status / currency | Reuse | In KB |",
    "|---|---|---|---|---|---|---|---|---|",
]
for i, s in enumerate(S_sorted, 1):
    r = cov[s["id"]]
    inkb = "yes" if r["ingested"] else "**NO**"
    if r["ingested"] and r["partial"]:
        inkb = "yes (partial)"
    L.append(
        f"| {i} | `{s['id']}` | [{s['title']}]({s['url']}) | {s['issuer']} | {s['jurisdiction']} | {s['doc_date']} | {s['version_status']} | {s['licence_note']} | {inkb} |"
    )

L += [
    "",
    "## Documents considered and deliberately NOT used",
    "",
    "- **Law-firm and consultancy commentaries** (Al Tamimi, Latham, Baker McKenzie, CMS, Trowers, Simmons, Pinsent Masons, KPMG, and similar). Useful for finding the primary documents, but they are copyrighted secondary sources, so they are not ingested and are not cited as authority.",
    "- **Arabic-only official PDFs** (for example the full text of Ministerial Resolution 51/2021). The KB is English-only in v1; the English ministry summary is used instead and labelled as a summary.",
    "- **DoH 'Encyclopedia of Health Legislation' Books 1, 3, 8** (Abu Dhabi, Feb 2023 issue). Book 8 covers the medical-products law that Federal Decree-Law 38/2024 has since replaced; not ingested to avoid stale law.",
    "- **TDRA IoT Regulatory Policy (English).** Only the Arabic policy and the English Procedures were found as primary files; the policy is a gap (listed under open items).",
    "- **Free-zone regimes** (DIFC, ADGM data protection, DHCC). Out of scope for v1; the PDPL itself excludes free zones that have their own data law.",
    "",
    "## Open items (what is still missing, and why)",
    "",
]
for s in S:
    if not cov[s["id"]]["ingested"]:
        L.append(f"- `{s['id']}`: {s['fetch'].get('reason', '')}")
L += [
    "- `UAE-PDPL-2021` is partial: 12 of 31 articles are in the KB. The full PDF is at https://uaelegislation.gov.ae/en/legislations/1972/download.",
    "- PDPL Executive Regulations: status not confirmed by this project (secondary sources disagree); not listed until a primary text is found.",
    "- UAE Media Law and executive regulations (current advertising regime): the National Media Council guide in the KB may predate them. Not yet located as primary text.",
    "- Cabinet Resolution 40/2019 (executive regulations of the medical liability law) and Federal Law 5/2019 (medicine practice): referenced in the KB texts, not ingested.",
    "",
    "## Draft input for the report template table: Y.3172 node to documents",
    "",
    "The ITU submission template asks, for each pipeline node, which policy documents support the requirement. This is the analyst's own first mapping from the registry (`nodes`, `dimensions`); it is **unreviewed** and will be refined on report days.",
    "",
    "| Y.3172 node | Miqyas component (draft) | Documents in the KB that bear on it |",
    "|---|---|---|",
]
node_desc = {
    "SRC": "Synthetic lab PDFs and wearable exports",
    "C": "Import collector (lab/wearable connectors)",
    "PP": "Normaliser and de-identifier",
    "M": "Coach model (K2 via gateway) and policy-adviser model",
    "P": "Policy node: policy and legal adviser plus safety guard",
    "D": "Distributor: routes outputs to member, partner clinic, authority",
    "SINK": "Member app, partner clinic inbox, authority report",
    "MLFO": "Coordinator (orchestrates agents and scenarios)",
    "SANDBOX": "Scenario simulator on synthetic data",
}
for n in ["SRC", "C", "PP", "M", "P", "D", "SINK", "MLFO", "SANDBOX"]:
    ids = [s["id"] for s in S if n in s["nodes"] and cov[s["id"]]["ingested"]]
    pend = [s["id"] for s in S if n in s["nodes"] and not cov[s["id"]]["ingested"]]
    cell = ", ".join(f"`{x}`" for x in ids) + (f" (pending: {', '.join(pend)})" if pend else "")
    L.append(f"| {n} | {node_desc[n]} | {cell} |")
L.append("")
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs" / "SOURCE_LIST.md").write_text("\n".join(L), encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print("wrote docs/SOURCE_LIST.md,", len(S), "sources")
