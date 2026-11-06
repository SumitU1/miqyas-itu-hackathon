"""Download the public source documents listed in sources/sources.json into kb/raw/.

Only sources with fetch.method == "http" are downloaded. Sources captured by hand
("browser") or still waiting for a person ("manual-pending") are reported, not fetched.
Nothing is executed from the downloaded files; they are only saved and hashed.

Usage:  python scripts/fetch_sources.py [--force]
"""
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "kb" / "raw"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    if dest.suffix.lower() == ".pdf" and not data.lstrip().startswith(b"%PDF"):
        raise RuntimeError("server returned something that is not a PDF (probably a bot-protection page)")
    dest.write_bytes(data)


def main() -> int:
    force = "--force" in sys.argv
    reg = json.loads((ROOT / "sources" / "sources.json").read_text(encoding="utf-8"))
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {}
    problems = 0
    done_files = set()
    for s in reg["sources"]:
        f = s["fetch"]
        dest = RAW / f["file"]
        m = f["method"]
        if m == "http":
            if f["file"] in done_files:
                continue
            done_files.add(f["file"])
            if dest.exists() and not force:
                status = "already present"
            else:
                try:
                    download(f["url"], dest)
                    status = "downloaded"
                except Exception as e:  # report and continue
                    status = f"FAILED: {e}"
                    problems += 1
        elif m == "browser":
            status = "hand-captured" if dest.exists() else "MISSING (hand-captured file not found)"
            if not dest.exists():
                problems += 1
        else:
            status = "manual-pending" + (" (file present)" if dest.exists() else " (file absent)")
        if dest.exists():
            manifest[f["file"]] = {
                "sha256": sha256(dest),
                "bytes": dest.stat().st_size,
                "source_id": s["id"],
                "url": f.get("url") or s["url"],
                "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            }
        print(f"{s['id']:<26} {m:<15} {status}")
    (RAW / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n{len(manifest)} files in kb/raw/, {problems} problem(s). Manifest: kb/raw/MANIFEST.json")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
