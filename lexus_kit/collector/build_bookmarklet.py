#!/usr/bin/env python3
"""Build bookmarklet.txt from capture.js without transforming JavaScript syntax."""
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
source = (HERE / "capture.js").read_text(encoding="utf-8")
# Drop the documentation header and indentation while keeping every JS token and
# line break intact. This gives a small, syntax-preserving compression without
# relying on a third-party minifier.
source = source[source.index("(async () => {"):]
compressed = "\n".join(line.strip() for line in source.splitlines())
(HERE / "bookmarklet.txt").write_text("javascript:" + quote(compressed, safe=""), encoding="utf-8")
