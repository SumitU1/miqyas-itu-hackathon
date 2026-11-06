# Agent layer (plan days 6-8): what is built, how it behaves, what it does not do

Code: `agents/`. Tests: `python -m unittest discover -s agents/tests -t .` (88 tests, no network, no model). Scenarios: `scenarios/S1-S4*.json`. Runner: `python -m agents.run_scenarios --all --out runs/<date>`.

> Public documents and synthetic members only. Not legal or medical advice. No lawyer or clinician has reviewed anything here. The Adviser words its answers as "the text says".

## 1. Parts

| File | Job |
|---|---|
| `agents/audit.py` | Append-only JSONL, each record holds the SHA-256 of the previous one. `verify_file` finds edits, deletions and reordering. A cut-off tail is only detectable against a published `head_hash` (the runner prints it into `summary.json`). |
| `agents/kbtool.py` | The only way agents read the KB. Scoped by source id; **every query is written to the audit log** (query, chunk ids, scores, evidence level, KB build id, scope). |
| `agents/roles.py` | The four roles. The three role agents have **disjoint KB scopes** (Coach: AI-ethics and AI-policy documents; Clinic: DHA/DoH sharing, telehealth, advertising; Authority: health-ICT law, data protection, localisation, cyber, device approval). The Adviser has no scope filter. |
| `agents/agent.py` | One class for Coach, Clinic and Authority. Retrieve in scope, ask the model for a structured assessment, **strip any citation that was not among the passages the agent was shown**, record it as a citation violation and lower confidence. A failed or unparseable model answer becomes `model_unavailable` + `escalate_to_human`, never a guess. |
| `agents/adviser.py` | Policy & Legal Adviser. `answer`: a ruling only when the evidence gate (rule v2) says `strong`, otherwise it **abstains without calling the model** and hands the best passages to a human. A ruling whose citations are not in what was retrieved is discarded. `verify`: for each citation, does it exist, does it fit the agent's own finding (rank under the same search), page, link, caveats read from the chunk record (revision date passed, summary only, non-binding, may be superseded, currency unconfirmed, partial capture, clinical-unreviewed). `detect_conflicts`: share versus withhold, citations spread over federal / Dubai / Abu Dhabi, missing assessments. Guidance, standards and summaries are never presented as binding: the system appends that note itself. |
| `agents/coordinator.py` | The Y.3172 MLFO role. Releases scenario chunks, collects assessments, calls the Adviser, writes the decision record, routes a ruling message. |
| `agents/guard.py` | A **fresh, minimal** keyword guard for the Coach: emergency language skips the model and points to 999 / 998; the Coach's draft reply is blocked if it contains a dose, a diagnosis or a guarantee. It is **not** a copy of the Phase 1 `miqyas-site` guard (that output filter still waits for a human safety review and held-out 2 is not met). Keyword rules are a floor, not a clinical safety system. |
| `agents/llm.py` | Gateway client, alias `auto` only (free pool). Key from `GATEWAY_LLM_KEY` or the `.env` named in `GATEWAY_ENV_FILE`; sent only as the auth header; never logged, printed or put in an error message (tested). The audit log records alias, the model the gateway says answered, and a hash of the prompt, not the prompt. |
| `agents/trace.py` | Rebuilds "why was this decided" from a log: trigger, assessments, cited chunks with page and link, Adviser answers, action, approval. Verifies the chain first and says so at the top. |
| `agents/scenario.py`, `agents/run_scenarios.py` | Load and validate scenarios (must declare `synthetic: true`; ID-, email- and phone-like strings are rejected); run them; write log, trace, decisions and summary per scenario. |

## 2. Protocol per scenario chunk
1. `chunk_release`: each agent gets only the facts addressed to it (plus what it already knew and the Coordinator's earlier rulings sent to it). An agent that has been told nothing yet is not asked.
2. Each agent returns `{finding, provisions, proposed_action{class,text}, confidence, open_questions}`; it never sees another agent's draft.
3. The Adviser verifies citations, flags conflicts, and answers the chunk's policy questions plus at most one open question per agent (cap 4). It never receives raw agent facts, only questions and passages.
4. Decision record: action = the **most protective** proposed class (emergency redirect > escalate > withhold > notify authority > revise claim > inform member > share > no action). `needs_human` is set for any data-transfer, clinical or public-claim step, any human-approval action class, conflict, Adviser abstention, citation violation or failed agent. Approval stays `pending` unless the scenario scripts one, which is logged `simulated: true`.
5. A `ruling` message carries the action class and the Adviser's own wording to the agents that took part, never free text written by another agent, so the Authority cannot learn clinical content from it.

Message envelope in the log: `{msg_id, scenario_id, round, from, to, type, payload, citations, kb_build_id, model_alias}` (+ `ts` and the chain fields on the record). The prompt hash is on the separate `model_call` record rather than on the message.

## 3. Reasoning trace
The trace is each agent's **stated rationale** (`finding`) plus the chunk ids it cited and the Adviser's verification. Hidden model reasoning is neither requested nor stored. The report must say this.

## 4. Known limits (say these in the report)
- Retrieval is lexical (BM25). Agents can only cite what the keyword search surfaces; `docs/RETRIEVAL_TESTS.md` lists the misses.
- The `fit to finding` check is the same BM25 ranking, so it is a plausibility check, not proof that a passage supports a claim. A human or a stronger model must still read the passage.
- Agent queries are derived from the scenario question and first fact, not planned by the model.
- Three roles share one model alias, so "different institutions" is by mandate (scope, facts, prompt), not by different models.
- The four documents still missing from the KB (FDL 38/2024, FL 15/2020, FDL 4/2016, WHO guidance) are listed in the role scopes and will be picked up after a rebuild; until then those parts of the law cannot be cited.
- The ITU reference code was not run (Ollama not installed, no decision from Sumit). The KB and agents are a re-implementation of its design, not its code.
- Synthetic members only. Nothing here claims data stays in the UAE.
