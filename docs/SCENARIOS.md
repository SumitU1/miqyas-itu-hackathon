# Scenario runs (plan days 9-10, first pass), 28 Oct 2026

Four synthetic error scenarios, three sequenced chunks each, run end to end on the free gateway alias `auto`. Outputs are in `runs/2026-10-28/S1..S4/` (`audit.jsonl`, `trace.md`, `decisions.json`, `summary.json`). Check any log: `python -m agents.verify_log runs/2026-10-28/S2/audit.jsonl --head <head_hash from summary.json>`.

> Synthetic members only. Not legal or medical advice. No lawyer or clinician has reviewed the knowledge base, the scenarios or any answer below. Model-written rulings contain inference; read them as "what the retrieved text appears to say", not as law.

## 1. What the four scenarios release, and who knows what

| Scenario | Chunks | Information given unevenly |
|---|---|---|
| S1 Red-flag lab result | critical potassium flag + risky question; emergency words in chat; lab import found to have been 6 h late | Coach holds the lab and chat; the Authority only gets a content-free incident report in chunk 3; the Clinic is never told |
| S2 Wearable localisation | wearable linked, cloud country unknown; vendor says Europe, consent text silent on transfer; clinic asks for all wearable data | Authority holds the data-flow description and vendor reply; Coach holds the consent text; Clinic only sees its own consent form in chunk 3 |
| S3 Clinic record sharing | clinic asks 12 months of labs; member moved to Abu Dhabi; clinic asks for the whole coach chat | Coach holds the consent scope and the mood notes; Clinic holds the request; Authority only hears about routing in chunk 2 |
| S4 AI health claim | draft ad promising results; influencer testimonial; AI-written personalised outcome messages | Coach holds the draft and the influencer facts; Clinic is asked to be named; Authority holds one complaint and no instruction on AI messages |

## 2. Results (one run each, all four chains verified)

| | S1 | S2 | S3 | S4 | Total |
|---|---|---|---|---|---|
| Decisions | 3 | 3 | 3 | 3 | 12 |
| Marked needs-human | 3 | 3 | 3 | 3 | 12 |
| Adviser questions | 6 | 12 | 12 | 12 | 42 |
| Adviser rulings (evidence `strong`) | 3 | 7 | 5 | 3 | 18 |
| Adviser abstentions (evidence `weak`, no ruling call) | 3 | 5 | 7 | 9 | 24 |
| Citations stripped (agent cited an id it was not shown) | 0 | 0 | 2 | 0 | 2 |
| Failed agent assessments | 0 | 0 | 0 | 0 | 0 |
| Model calls (failed) | 12 (0) | 28 (0) | 27 (0) | 23 (0) | 90 (0) |
| Audit records | 73 | 132 | 139 | 135 | 479 |

Models that answered (all through `auto`, the gateway's free pool; none was a Claude model): `IFM/K2-Horizon-375B-A23B`, `dots-studio/dots-3-note-preview:free`, `qwen/qwen3.8-27b`, `@cf/qwen/qwen3.8-27b`, `poolside/laguna-s-2.1:free`. The gateway picks per call, so two runs of the same scenario can differ. I read the served-model names from the gateway's replies; I did not audit its billing per call.

## 3. What the runs show

- **Abstention works as designed.** For 24 of 42 Adviser questions no ruling was attempted because the evidence gate said `weak` (the optional query-planning call still ran for these; no ruling call did). S4 chunk 3 (AI-written personalised health messages) got no ruling on any of its four questions, which is the observable form of candidate gap G5 (`docs/POLICY_GAPS_CANDIDATES.md`).
- **Information asymmetry is visible.** In S2 chunk 2 the Coach says the Federal Law 2/2019 articles named in the Coordinator's message are not in its own passages and so it cannot ground a statement on them, and escalates instead of guessing.
- **Guard behaviour.** S1: the member's "chest tight, can't breathe" skipped the model and returned the 999/998 message; the critical-potassium draft reply told the member to seek urgent care and gave no diagnosis or dose. S4: the keyword guard blocked a Coach note that merely *quoted* the advert's word "guaranteed" and replaced it with the generic "no diagnosis or dose" text, a **false positive** (see limits).
- **Cross-check on citations.** The two stripped citations in S3 were decision ids (`S3-C1-D`) copied from a routed message, not chunk ids; the check removed them and lowered confidence.
- **A candidate gap shown in a ruling.** S2 chunk 2: the Adviser, asked whether explicit consent is enough, cited PDPL Art. 23 and also noted that the PDPL steps aside for health data with its own law and that the Executive Regulations are unconfirmed (G1, G2, G6). It did not settle which regime applies; a human has to.
- **Query planning raised the ruling rate.** A first S1 run before planning was added gave 1 ruling in 7 questions (kept locally in the git-ignored `runs/scratch/`); with the Adviser trying up to three short keyword rewrites it gave 3 of 6. Planning only adds candidate queries, every query is logged, and the evidence level in the record is the level of the query that was used. Scenario questions were written before any run and not changed afterwards.

## 4. Limits to state in the report
- One run per scenario. Model choice varies per call; a rerun will not be identical. No statistics are claimed.
- Rulings are model-written from retrieved passages. They sometimes add inference ("so the health ICT law governs") beyond the text. The `fit to finding` and `binding` markers are mechanical aids, not legal review.
- The `jurisdiction-spread` flag fired in 10 of 12 decisions. It is coarse (any citations from two of federal / Dubai / Abu Dhabi), so it carries little signal on its own.
- All 12 decisions were marked needs-human. That is the intended conservative setting for this domain, but it means the runs do not exercise a "safe to proceed" path.
- Agents sometimes apply a document whose reach to a consumer app is itself unclear (in S2 the Authority applied the Abu Dhabi ADHICS standard to a Dubai-based member's data flow). That is gap G1/G4 territory, not something the system resolves; the jurisdiction flag only points at it.
- Scenario approvals are scripted (two of twelve, marked `simulated`); nobody approved anything.
- The four manual PDF downloads are still missing from the KB, so no answer here can cite FDL 38/2024, FL 15/2020, FDL 4/2016 or the WHO guidance.
- The keyword guard produced one false positive and has never been red-teamed.
