#!/usr/bin/env bash
# Verify required legal texts and source-bound evidence, not manual approvals.
set -euo pipefail
python3 - <<'PYTHON'
import sys
from pathlib import Path
sys.path.insert(0, "scripts")
from legal import legal_files, verify_legal

root = Path.cwd()
for name in legal_files(root, required=True):
    if not (root / name).read_text(encoding="utf-8").strip():
        raise RuntimeError(f"Empty required legal text: {name}")
verify_legal(root)
PYTHON
