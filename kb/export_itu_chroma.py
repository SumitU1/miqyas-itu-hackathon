"""Load KB v1 into a ChromaDB store using the ITU reference repo's schema (collection 'kb_main').

STATUS: written on 2026-10-26, NOT YET RUN. It needs two things this machine does not have yet:
  1. `pip install chromadb ollama`
  2. a running Ollama server with the embedding model:  ollama pull nomic-embed-text

It mirrors CrashingGuru/ITUAIReadiness simulation/server/knowledge/kb.py and ingest.py:
  - collection "kb_main", cosine space, one record per chunk, embeddings supplied by us
  - metadata keys used by the ITU code: source_file, source_type, country, chunk_index,
    total_chunks, ingested_at, document_category
  - plus our citation keys (source_id, chunk_id, citation, locator, url, doc_date,
    version_status, redistribute, review_status, clinical_review) and stable ids (the ITU code
    uses random UUIDs, which cannot be cited).

Usage:  python kb/export_itu_chroma.py [--public] [--reset]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FULL = ROOT / "kb" / "out" / "chunks.jsonl"
PUBLIC = ROOT / "kb" / "out" / "public" / "chunks_public.jsonl"
CHROMA_DIR = ROOT / "kb" / "out" / "chroma"

TYPE_MAP = {"standard": "standards_document", "law": "policy_document", "regulation": "policy_document",
            "policy": "policy_document", "guideline": "policy_document", "strategy": "national_strategy"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--public", action="store_true", help="export the shareable excerpts instead of full text")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--ollama", default="http://localhost:11434")
    ap.add_argument("--model", default="nomic-embed-text")
    a = ap.parse_args()
    try:
        import chromadb
        import ollama
    except ImportError as e:
        print("Missing package:", e, "\nInstall with: pip install chromadb ollama")
        return 2

    rows = [json.loads(l) for l in (PUBLIC if a.public else FULL).read_text(encoding="utf-8").splitlines() if l.strip()]
    total = {}
    for r in rows:
        total[r["source_id"]] = total.get(r["source_id"], 0) + 1

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if a.reset:
        try:
            client.delete_collection("kb_main")
        except Exception:
            pass
    col = client.get_or_create_collection("kb_main", metadata={"hnsw:space": "cosine"})
    oc = ollama.Client(host=a.ollama)
    now = datetime.now(timezone.utc).isoformat()
    B = 16
    for i in range(0, len(rows), B):
        batch = rows[i:i + B]
        emb = oc.embed(model=a.model, input=[r["text"][:2000] for r in batch])["embeddings"]
        col.upsert(
            ids=[r["chunk_id"] for r in batch],
            documents=[r["text"] for r in batch],
            embeddings=emb,
            metadatas=[{
                "source_file": r["source_id"],
                "source_type": TYPE_MAP.get(r["kind"], "policy_document"),
                "country": "United Arab Emirates" if r["jurisdiction"] != "international" else "global",
                "chunk_index": str(r["ordinal"]),
                "total_chunks": str(total[r["source_id"]]),
                "ingested_at": now,
                "document_category": "UAE_Health_Policy",
                "source_id": r["source_id"], "chunk_id": r["chunk_id"], "citation": r["citation"],
                "locator": r["locator"], "url": r["url"], "doc_date": r["doc_date"],
                "version_status": r["version_status"], "redistribute": r["redistribute"],
                "review_status": r["review_status"], "clinical_review": r["clinical_review"],
            } for r in batch],
        )
        print(f"  {min(i + B, len(rows))}/{len(rows)}", end="\r")
    print(f"\nkb_main now holds {col.count()} records at {CHROMA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
