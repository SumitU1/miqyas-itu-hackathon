# Review of the ITU reference code (`CrashingGuru/ITUAIReadiness`) and the reuse decision

Reviewed 2026-10-26 by reading the files on GitHub (raw copies saved to a scratch folder, read as text). **Nothing from that repo was installed or executed.**

## What the repo is

- A teaching project for the **ITU AI Readiness Framework 2025**: an "AI Readiness Simulation Game" in `simulation/`. FastAPI server, a command-line client, 6 small agents, a ChromaDB knowledge base, SQLite sessions, a NetworkX "what-if" graph, and 57+ national AI strategy PDFs as seed documents.
- Licence: MIT. Last push 2026-10-20. 3 stars. Language: Jupyter Notebook / Python.
- The hackathon page names this repo as "reference code for knowledge base creation".

## Files read

`README.md`, `simulation/README.md`, `simulation/PARTICIPANT_GUIDE.md`, `requirements.txt`, `setup.sh`, `Dockerfile`, `docker-compose.yml`, `server/config.py`, `server/knowledge/ingest.py`, `server/knowledge/kb.py`, `server/knowledge/cache.py`, `server/knowledge/dimensions.py`, `server/agents/base.py`, `server/routes/query.py`, `InputDocs/Inputs.md`, the Y.3172 and Sandbox summary text files.

## Safety read (before any thought of running it)

- No network calls other than to a local Ollama server (`http://localhost:11434`); `setup.sh` pulls two Ollama models (`qwen2.5:14b`, about 4.7 GB, and `nomic-embed-text`, about 274 MB) and then runs the ingest. No `eval`/`exec`/`subprocess`/shell-out in the knowledge or config code. No telemetry beyond ChromaDB's `anonymized_telemetry=False`.
- Dependencies are ordinary (`ollama`, `chromadb`, `fastapi`, `uvicorn`, `sqlmodel`, `httpx`, `rich`, `networkx`, `PyMuPDF`, `pydantic`). `docling` is an optional import for PDF parsing.
- The game needs about 16 GB of RAM for the 14B model. The **ingest alone** only needs the small embedding model.

## How its ingestion works

1. **Parse**: PDF via `docling`, falling back to PyMuPDF; `.txt/.md/.csv/.html` as plain text.
2. **Chunk**: split on whitespace into windows of words. `config.py` sets 256 words with 30 overlap (the docstring says 512/50; the config wins). Hard cap of 2,000 characters per chunk.
3. **Embed**: Ollama `nomic-embed-text`, batches of 16.
4. **Store**: ChromaDB, cosine space, collections `kb_main`, `kb_framework`, `kb_decisions`, `kb_usecase`; random UUID ids.
5. **Metadata per chunk**: `source_file`, `source_type` and `country` (both **guessed from the file name with regexes**), `chunk_index`, `total_chunks`, `ingested_at`, `document_category` (from the sub-folder).

## What it does not give us (why we cannot use it as is)

| Need (from the brief: "source attribution", "auditability") | ITU ingest |
|---|---|
| Page or article for each chunk | No page, no section, no article number |
| Canonical URL, issuer, document date, version | None; only the file name |
| Licence or reuse note | None |
| Stable ids that an audit log can cite | Random UUIDs, new on every run |
| Review status (legal / clinical) | None |
| UAE as a country | Not in its country list: UAE files would be tagged `global`; the source-type regexes also misfile some names |
| Section-aware chunking for laws (one article per chunk) | No: it chops words straight through article boundaries |
| Runs here today | Needs Ollama; none is installed on this PC |

## Decision

**Reuse the design and the schema; do not run the code as is.**

- `kb/build_kb.py` follows the same flow (parse, chunk by words at 256/30, per-chunk metadata) and adds the citation fields above plus article-aware splitting for laws.
- `kb/export_itu_chroma.py` loads our chunks into a Chroma `kb_main` collection with the **ITU metadata keys** plus ours, so the ITU agents or a judge's tooling can read the same store. **It has not been run yet** (needs `pip install chromadb ollama` and `ollama pull nomic-embed-text`).
- Retrieval in v1 is BM25 (offline, deterministic). Dense retrieval is the planned upgrade once the Chroma export has been run.

## Open decisions for Sumit

1. **Is a re-implementation acceptable, or should we run the ITU `ingest.py` unchanged?** The brief says to *use* the reference code. A safe way to satisfy it: install Ollama (one app, about 300 MB for the embedding model), run the ITU ingest on our raw documents as a cross-check on day 6, and say so in the report. This needs your go because it installs software.
2. **ITU sandbox cloud credits.** Not requested; they need the final team sheet.
