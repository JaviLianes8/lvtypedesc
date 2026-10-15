"""Fetch the public references the source tests read, and record them in MANIFEST.json.

The copies stay on the maintainer's machine (git ignores them); only the manifest with each
URL, date, size and SHA-256 is tracked. Run from the repository root:

    python scripts/fetch_sources.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import urllib.request
from pathlib import Path

_NI = "https://docs-be.ni.com/api/bundle/labview/page/"
SOURCES = {
    "ni-type-descriptors.json": _NI + "type-descriptors.html",
    "labviewwiki-type-descriptor.html": "https://labviewwiki.org/wiki/Type_descriptor",
}
LICENCES = {
    "ni-type-descriptors.json": "NI documentation, copyright NI; local copy only",
    "labviewwiki-type-descriptor.html": "LabVIEW Wiki page, its own licence; local copy only",
}

FOLDER = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sources"


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    entries = []
    for name, url in SOURCES.items():
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/plain"}
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
        (FOLDER / name).write_bytes(body)
        entries.append(
            {
                "file": name,
                "url": url,
                "fetched": today,
                "size": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "licence": LICENCES[name],
            }
        )
    manifest = {"note": "public references fetched for the source tests", "files": entries}
    text = json.dumps(manifest, indent=2) + "\n"
    (FOLDER / "MANIFEST.json").write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
