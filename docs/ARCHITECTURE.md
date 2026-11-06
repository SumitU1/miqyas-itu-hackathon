# Architecture v0.2: a policy-grounded UAE health agent (one page)

> v0.2 (28 Oct 2026): sections 2-4 are now implemented in `agents/`; see `docs/AGENTS.md` for what was built and its limits, and `docs/SCENARIOS.md` for the first scenario runs. Differences from v0.1: the Coach uses a fresh minimal guard, not a copy of the Phase 1 guard; the Adviser may plan up to three keyword queries per question (all logged); message envelopes carry the prompt hash on the separate `model_call` record.

**What it is.** Miqyas is a lifelong health record and coach for people in the UAE. For the ITU AI for Good hackathon we build a small, separate system around it: agents that must act inside the rules in the public UAE health-policy documents, and that show **which rule, which page** each decision came from. Synthetic members and public documents only. Not legal advice; nothing here is reviewed by a lawyer or a clinician.

```
 sequenced scenario chunks (synthetic)            ITU-T Y.3172 pipeline
            |                                       SRC -> C -> PP -> M -> P -> D -> SINK
            v                                       with MLFO (orchestrator) and ML sandbox
   +-------------------+   scoped information    +-----------------------------------------+
   |   COORDINATOR     |------------------------>|  Miqyas Coach agent        (M)          |
   |  (Y.3172 MLFO)    |   each agent gets only  |  Partner Clinic agent      (SINK/D)     |
   |  runs rounds,     |   what its mandate      |  Health-Data Authority     (regulator)  |
   |  routes messages  |   entitles it to        +----------------+------------------------+
   +---------+---------+                                          | independent assessments
             |                                                    v (structured, each with citations)
             |                                 +------------------------------------------+
             |  rulings, conflicts             |  POLICY & LEGAL ADVISER agent   (P node) |
             +<--------------------------------|  reads the whole KB, checks citations,   |
             |                                 |  abstains unless evidence is "strong"    |
             v                                 +----------------+-------------------------+
   +-------------------+                                        | KB queries
   | DECISION RECORD   |   human approval required for          v
   | action, owner,    |   any clinical or data-transfer   +---------------------------+
   | human-in-loop     |   action                          |  KNOWLEDGE BASE v1        |
   +---------+---------+                                   |  23 sources, 688 chunks,  |
             v                                             |  citation on every chunk  |
   +---------------------------------------------------------------------------------+
   | AUDIT LOG: append-only, hash-chained JSONL. Every message, KB query (query, chunk |
   | ids, scores, evidence level), model call (alias, prompt hash), decision, approval |
   +---------------------------------------------------------------------------------+
```

## 1. Knowledge base (built, days 1-5)
`sources/sources.json` (27 listed sources) -> `kb/build_kb.py` -> chunks of 256 words (30 overlap, as in the ITU reference config), one article per chunk for laws. **Every chunk carries**: source id, article or section, PDF page range, canonical URL, document date, version note, licence handling, `not-legally-reviewed`, and `clinical-unreviewed` where the document has clinical content, plus hashes of the raw file and the chunk. Retrieval is BM25 (offline, deterministic) with an **evidence gate**: `strong` / `weak` / `none`. Agents may answer from the KB alone only on `strong`. Measured results: `docs/RETRIEVAL_TESTS.md`. Coverage and gaps: `docs/KB_COVERAGE.md`.

## 2. Agents (to build, days 6-8). Each has a *mandate* and sees different information
| Agent | Role in the brief | Mandate (KB filter) | Sees | Must not |
|---|---|---|---|---|
| Miqyas Coach | innovative solution | Miqyas product rules; AI-ethics documents | the member's synthetic record, the coach's own outputs | give a diagnosis; move data without a ruling |
| Partner Clinic | institutional participant | DHA/DoH sharing, telehealth, advertising standards | only records the member consented to share | read the rest of the member record |
| Health-Data Authority | regulator (MOHAP / DHA / DoH / UAE Data Office) | localisation, consent, data protection, device approval | incident reports and data-flow descriptions, not clinical content | act without a documented trigger |
| Policy & Legal Adviser | policy and legal adviser | the whole KB | questions from any agent | answer on `weak` or `none` evidence; present a summary as the binding text |

The Coach reuses the Phase 1 coach and safety guard, **copied into this repo as a minimal module** (never importing the production `miqyas-site` repo). Model: an OpenAI-compatible model gateway `auto` (K2 first), free tier only.

## 3. Coordination protocol (Y.3172 MLFO role)
Per scenario chunk the Coordinator runs rounds: (1) **release** the chunk to each agent with its scoped view; (2) each agent returns a **structured assessment** `{finding, provisions[chunk ids], proposed_action, confidence, open_questions}` with no access to the others' drafts; (3) the Adviser **verifies** every cited chunk exists and supports the claim, **flags conflicts** between assessments and between jurisdictions (Dubai DHA versus Abu Dhabi DoH versus federal); (4) the Coordinator writes a **decision record** and marks it `needs-human` for any clinical, data-transfer or public-claim action; (5) the next chunk is released with the incomplete or uneven information the brief asks for. Message envelope: `{msg_id, scenario_id, round, from, to, type, payload, citations, kb_build_id, model_alias, prompt_hash, ts}`.

## 4. Audit trail and reasoning trace
One JSONL file per run; each record holds the hash of the previous record, so a missing or edited line is detectable. A small viewer rebuilds "why was this decided" as: trigger -> assessments -> cited chunks (with page and URL) -> ruling -> approval. The **reasoning trace is the model's stated rationale plus its cited chunk ids**, not hidden internal reasoning; the report will say so.

## 5. ITU-T Y.3172 mapping (draft, unreviewed)
SRC synthetic lab PDFs and wearable exports; C import collector; PP normaliser and de-identifier; M coach model and adviser model; **P policy node = the Policy & Legal Adviser plus the safety guard**; D distributor to member, clinic or authority; SINK member app, clinic inbox, authority report; MLFO the Coordinator; ML sandbox the replayable scenario runner on synthetic data. Document-to-node table: `docs/SOURCE_LIST.md`.

## 6. Hard limits
Synthetic data only. No claim that data stays in the UAE (not confirmed in writing; the hosting provider's position is open). Nothing is pushed, published or submitted without Sumit's go. Dr. Neeta is an adviser, not "medical lead"; all clinical entries stay `clinical-unreviewed` until a clinician signs off.
