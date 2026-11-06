# Miqyas × ITU AI for Good Hackathon (UAE): policy-grounded health agent

Submission workspace for the **ITU AI for Good Sandbox Hackathon, United Arab Emirates** (submission due 10 Nov 2026). This is a **new, clean repository**: it is not the production `miqyas-site` repo and contains no member data.

**Status (Nov 2026):** submission to the ITU AI for Good Sandbox Hackathon, United Arab Emirates. Research prototype. Four synthetic scenarios run end to end; see docs/ROADMAP_STATUS.md for what is built, partly built and not built.

> Public documents and synthetic data only. Nothing in this repo is legal or medical advice. No UAE lawyer and no clinician has reviewed any of it.

## Read these first

| File | What it is |
|---|---|
| [docs/SOURCE_LIST.md](docs/SOURCE_LIST.md) | The public UAE health-policy documents: URL, issuer, date, status, reuse note |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | One-page design: knowledge base, policy and legal adviser, role agents, coordination, audit log, ITU-T Y.3172 mapping |
| [docs/KB_COVERAGE.md](docs/KB_COVERAGE.md) | What is in the knowledge base against the source list, what is missing, integrity checks |
| [docs/RETRIEVAL_TESTS.md](docs/RETRIEVAL_TESTS.md) | Retrieval test results, including the untuned baseline and a held-out set |
| [docs/ITU_REFERENCE_CODE_REVIEW.md](docs/ITU_REFERENCE_CODE_REVIEW.md) | Review of the ITU reference code and the reuse decision |
| [docs/POLICY_GAPS_CANDIDATES.md](docs/POLICY_GAPS_CANDIDATES.md) | Candidate policy and standards gaps found so far (unverified) |
| [docs/AGENTS.md](docs/AGENTS.md) | The agent layer: parts, protocol, audit log, known limits |
| [docs/SCENARIOS.md](docs/SCENARIOS.md) | First run of the four scenarios: numbers, what they show, limits |
| [docs/ROADMAP_STATUS.md](docs/ROADMAP_STATUS.md) | What is built, partly built, not built; bugs fixed; speed-up numbers |

## After a fresh clone

The full text of the source documents is not in this repository; `kb/out/public/chunks_public.jsonl` holds 60-word excerpts with links. Without a rebuild, search and most tests run on those excerpts and 20 tests that need the full text are skipped (151 run, 0 fail). Steps 1 and 2 below rebuild the full text, after which all 151 run.

## Run it

Needs Python 3.10+ and PyMuPDF (`pip install pymupdf`). No other packages, no model, no network after step 1.

```bash
python scripts/fetch_sources.py        # 1. download the public documents into kb/raw/ (about 60 MB)
python kb/build_kb.py                  # 2. build the knowledge base (kb/out/)
python kb/search.py "may health data be stored outside the UAE"   # 3. ask it something
python -m unittest discover -s kb/tests -p "test_*.py"             # tests
python kb/run_retrieval_tests.py --label "my run"                  # retrieval test queries
python kb/coverage.py                                               # coverage check
python -m unittest discover -s agents/tests -t .                    # agent-layer tests (no model, no network)
python -m agents.run_scenarios --all --out runs/2026-10-28          # run the four scenarios (needs the gateway key, see docs/AGENTS.md); add --jobs 4 --workers 4 to run faster
python scripts/bench.py --workers 4 --compare docs/bench/golden_retrieval.json   # benchmark, no network
python -m agents.verify_log runs/2026-10-28/S2/audit.jsonl          # check an audit log's hash chain
```

Two sources were captured by hand from bot-protected official pages (`UAE-PDPL-2021`, `MOHAP-MD51-2021`) and four are waiting for a person to download a file; see `docs/KB_COVERAGE.md` section 3. The raw files are **not** committed (licence position unclear); `kb/out/public/chunks_public.jsonl` is the shareable export (a 60-word excerpt per chunk plus citation and link).

## Layout

```
sources/sources.json        registry: one entry per document (the source of truth)
scripts/                    fetch_sources.py, make_source_list.py
kb/build_kb.py              parse -> chunk (256/30 words, one article per chunk for laws) -> citation per chunk
kb/search.py                BM25 retrieval + evidence gate (strong / weak / none)
kb/export_itu_chroma.py     loads the chunks into the ITU reference ChromaDB schema (written, NOT yet run)
kb/coverage.py              coverage and integrity checks
kb/tests/                   unit tests and the retrieval test cases
agents/                     audit log, KB tool, role agents, adviser, coordinator, guard, trace, runner (+ agents/tests/)
scenarios/                  four synthetic error scenarios in sequenced chunks
runs/                       scenario run outputs: audit.jsonl, trace.md, decisions.json, summary.json
docs/                       the documents listed above
```

## Rules this repo follows

- Synthetic data and public documents only; no secrets, no production database, no code the live site depends on.
- Model for the agents: any OpenAI-compatible endpoint, set with `GATEWAY_URL`, alias `auto`. The published runs used a free model pool. The key is read from `GATEWAY_LLM_KEY` or the file named in `GATEWAY_ENV_FILE`, and is never printed or logged.
- No claim that data stays in the UAE.
- Clinical content is labelled `clinical-unreviewed`; nobody is named as medical lead.
