#!/usr/bin/env bash
# Fail before an expensive CI build when distribution licensing is unapproved.
set -euo pipefail
for file in LICENSE NOTICE; do
  [[ -s "$file" ]] || { echo "Missing/nonempty required text: $file" >&2; exit 1; }
done
for name in APPROVED_LICENSE_SHA256 APPROVED_NOTICE_SHA256; do
  digest="${!name:-}"
  [[ "$digest" =~ ^[0-9a-f]{64}$ ]] || { echo "$name must contain the approved lowercase SHA-256 digest." >&2; exit 1; }
done
[[ "$(sha256sum LICENSE | cut -d ' ' -f 1)" == "$APPROVED_LICENSE_SHA256" ]] || { echo 'LICENSE approval digest mismatch.' >&2; exit 1; }
[[ "$(sha256sum NOTICE | cut -d ' ' -f 1)" == "$APPROVED_NOTICE_SHA256" ]] || { echo 'NOTICE approval digest mismatch.' >&2; exit 1; }
