#!/usr/bin/env bash
set -euo pipefail
expected="kkgams/$(python3 -c 'import json; print(json.load(open("component.json"))["name"])')"
[[ "${GITHUB_REPOSITORY:?}" == "$expected" ]] || { echo 'Noncanonical repository' >&2; exit 1; }
version="$(cat version.txt)"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || exit 1
if [[ "${GITHUB_REF:?}" == refs/tags/* ]]; then
  [[ "$GITHUB_REF" == "refs/tags/v$version" ]] || exit 1
else
  [[ "${GITHUB_EVENT_NAME:?}" == workflow_dispatch && "$GITHUB_REF" == refs/heads/release ]] || exit 1
fi
bash scripts/check-licensing-digests.sh
python3 scripts/check-source.py
python3 -c 'import sys; from pathlib import Path; sys.path.insert(0, "scripts"); from legal import verify_legal; verify_legal(Path.cwd())'
