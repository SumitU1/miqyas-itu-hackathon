# Roadmap status, bugs fixed and speed-up (28 Oct 2026)

Private and local: nothing pushed, nothing submitted, no public repository. Python 3.13, no packages beyond PyMuPDF. There is no linter or type checker installed on this machine and none was installed; the "static" checks below are `python -W error` on the whole test run and `compileall`.

## 1. Baseline (before this pass)

| Check | Result |
|---|---|
| `python -W error -m unittest discover -s agents/tests -t .` | 99 tests pass |
| `python -W error -m unittest discover -s kb/tests` | 13 tests pass |
| `python kb/coverage.py` | all checks PASS (23 of 27 sources ingested, 689 chunks) |
| `python -m agents.verify_log` on S1-S4 | 4 of 4 chains verify against the published head hashes |
| Real gateway run of S1-S4 (commit 617cf2a) | 0 failed calls; 222-447 s per scenario, one model call at a time (read off the console, not saved) |

How to run everything is in the root `README.md` ("Run it"). The agent-layer tests need no model and no network.

## 2. Roadmap: built, partly built, not built

| Item | State | Where |
|---|---|---|
| Source list (27 documents) | Built | `docs/SOURCE_LIST.md`, `sources/sources.json` |
| Knowledge base v1, per-chunk citations, evidence gate | Built | `kb/`, `docs/KB_COVERAGE.md`, `docs/RETRIEVAL_TESTS.md` |
| Four manual PDFs (4 of 27 sources) | **Not built, needs Sumit to download them** | `docs/KB_COVERAGE.md` section 3 |
| Policy and legal adviser (abstains unless evidence is strong, checked citations) | Built | `agents/adviser.py`, `docs/AGENTS.md` |
| Three role agents with separate scopes and facts | Built | `agents/agent.py`, `agents/roles.py` |
| Coordinator and message protocol | Built | `agents/coordinator.py` |
| Hash-chained audit log and verifier | Built | `agents/audit.py`, `agents/verify_log.py` |
| Trace viewer ("why was this decided") | Built | `agents/trace.py` |
| Four synthetic scenarios, validator, runner | Built | `scenarios/`, `agents/scenario.py`, `agents/run_scenarios.py`, `docs/SCENARIOS.md` |
| Concurrent model calls | Built in this pass | `agents/coordinator.py`, `docs/bench/` |
| Policy-gap analysis from the runs | Partly built (candidates only, unverified) | `docs/POLICY_GAPS_CANDIDATES.md` |
| Comparison against the ITU reference stack | Not built: Ollama and the ITU script are not installed or run; the KB and agents are a re-implementation | `docs/ITU_REFERENCE_CODE_REVIEW.md` |
| Legal and clinical review | Not built: nobody has reviewed anything | all docs say so |
| Several runs per scenario, to see how much replies vary | Not built: one run each | `docs/SCENARIOS.md` |
| Report, video, submission (due 10 Nov) | Not built | days 11-15 |

## 3. Bugs found and fixed

Each fix was written test-first (the test failed, then passed). Verify with `python -W error -m unittest discover -s agents/tests -t .` (116 tests).

| # | Bug | Effect | Fix | Test |
|---|---|---|---|---|
| 1 | The audit log was not thread-safe | With any concurrency, two records could take the same sequence number or point at the same previous hash, breaking the chain | One lock around number, hash and file write | `test_audit.test_concurrent_appends_from_many_threads_keep_one_valid_chain` |
| 2 | The gateway client's call counter was not thread-safe | Under threads the count could be wrong | Lock | covered by the concurrent coordinator tests |
| 3 | A model that returned a string where a list was asked for (`"provisions": "UAE-X:0001"`) was read letter by letter | Every character became a citation violation, or became an "open question" for the Adviser | `llm.as_list` used for provisions, conditions, open questions and planned queries | `test_agent`, `test_adviser`, `test_llm.AsList` |
| 4 | `jurisdiction-spread` fired whenever federal law and one emirate were both cited (10 of 12 decisions) | Almost every decision was flagged, so the flag told a reviewer nothing | Fires only when both Dubai and Abu Dhabi are cited | `test_adviser.test_federal_law_plus_one_emirate...` |
| 5 | The Coach output guard blocked "I cannot guarantee ..." and "not a cure" | A correct, careful reply was replaced by the safe fallback (seen once in S4) | Negated phrases are ignored | `test_guard.test_negated_mentions_are_not_claims` |
| 6 | A blocked reply did not say which phrase tripped the rule | A reviewer could not tell a real violation from a false one | The surrounding phrase is stored in the `guard` record | `test_guard.test_a_blocked_reply_records_the_phrase...` |
| 7 | A scenario with `facts` given as one string, a blank question, or a per-role question with no default was accepted | The string was fed to the agent letter by letter, or an agent was asked an empty question | Validator rejects all three, plus non-list `policy_questions` | `test_scenarios` (3 new tests) |
| 8 | The runner with no scenario and no `--all` did nothing and exited 0; a missing key or file printed a traceback | Easy to think a run had succeeded | Exit code 2 with a one-line message | `test_runner` (4 new tests) |
| 9 | Trace citation line had a pair of replace calls that did nothing | Dead code | Removed | `test_trace` still passes |

Not fixed: the Adviser prompt does not say that decision ids such as `S3-C1-D` are not chunk ids (the earlier runs saw two stripped citations of that kind; the check catches them, so this is a quality issue, not a safety one).

## 4. Changelog

- `Coordinator(workers=N)`: the three role assessments run side by side with the Adviser's scripted questions; agents' own open questions start as soon as they exist. Messages are written in a fixed order after the results are in, so the log of a parallel run has the same message trail and the same decisions as a sequential one (`workers=1`).
- `python -m agents.run_scenarios`: `--workers N` (calls in flight inside a scenario), `--jobs N` (scenarios side by side), one shared KB index instead of one per scenario.
- `scripts/bench.py` with a golden retrieval file: speed-ups must not change a single retrieved passage or score.
- Fixes 1-9 above.
- Tests: 99 to 116 agent-layer tests (kb tests unchanged, 13).

## 5. Metrics

Method: `scripts/bench.py`, no network. Scenario S2 runs end to end with a scripted model that sleeps 0.25 s per call, standing in for the gateway (which took 4-8 s per call). Same 19 model calls before and after. KB figures are the median of 5 loads and the best of 5 passes over the 66 retrieval test queries. `--compare` checks every query's ranked passages and scores against the saved golden file.

```bash
python scripts/bench.py --workers 1 --out docs/bench/before.json --golden docs/bench/golden_retrieval.json   # before
python scripts/bench.py --workers 4 --out docs/bench/after.json --compare docs/bench/golden_retrieval.json   # after
```

| Metric | Before (`workers=1`) | After (`workers=4`) | Change |
|---|---|---|---|
| S2 end to end, simulated 0.25 s gateway | 4.81 s | 1.55 s | **68% less time (3.1x faster)** |
| Model calls in that run | 19 | 19 | same |
| Audit chain verifies | yes | yes | same |
| Retrieved passages and scores (66 queries) | golden | identical | no change |
| KB search, mean per query | 0.51-0.58 ms | 0.57 ms | no change (never the bottleneck) |
| KB load | 115-131 ms | 130-170 ms | noise on a busy machine, no change in code |
| Peak memory while loading the KB | 11.4 MB | 11.4 MB | same |

**Real gateway (alias `auto`, free pool), measured today, not simulated:**

| Measurement | Result |
|---|---|
| 4 identical tiny calls, one at a time | 40.8 s (about 10 s per call) |
| The same 4 calls at once (4 threads) | 7.9 s, all 4 succeeded: **5.2x faster**, so the gateway does serve calls side by side |
| Scenario S3 end to end, `--workers 4` | 301 s, 31 model calls, 0 failed, chain verified |

What this does and does not show. The first two rows are a clean before/after on the real gateway: concurrency works. The S3 row is one run. I have no saved sequential S3 time to compare it with: the earlier sequential runs (222-447 s per scenario) were read off the console and not stored, and replies differ run to run (27 calls then, 31 now), so I am **not** claiming a measured end-to-end speed-up on the real gateway. The simulated run (68% less time, same calls, same decisions) is the reproducible figure. To close this: run `--workers 1` and `--workers 4` on the same scenario back to back, a few times each.

## 6. What stopped this being more

- A literal overnight run was not possible in one session; this is what fitted in it.
- The simulated figure is a model of the gateway, not a measurement of it. The real-gateway figures are in section 5 and vary from run to run.
- The knowledge base is missing 4 of 27 sources until the PDFs are downloaded.
- Review by a lawyer and a clinician is outside what this repository can do.
