#!/usr/bin/env bash
# GitHub API errors cannot be interpreted as an absent version tag.
set -euo pipefail
: "${GH_TOKEN:?required}"
: "${GITHUB_REPOSITORY:?required}"
: "${GITHUB_REF_NAME:?required}"
[[ "$GITHUB_REPOSITORY" == 'kkgams/plugin.tile-detect' ]] || { echo 'Unexpected repository' >&2; exit 1; }
version="$(tr -d '[:space:]' < version.txt)"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Invalid distribution version' >&2; exit 1; }
[[ "$GITHUB_REF_NAME" == "v${version}" ]] || { echo 'Unexpected release tag' >&2; exit 1; }
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
if ! status="$("${CURL_BIN:-curl}" --silent --show-error --output "$work/release.json" --write-out '%{http_code}' \
  --header "Authorization: Bearer ${GH_TOKEN}" \
  --header 'Accept: application/vnd.github+json' \
  --header 'X-GitHub-Api-Version: 2022-11-28' \
  "https://api.github.com/repos/${GITHUB_REPOSITORY}/releases/tags/${GITHUB_REF_NAME}")"; then
  echo 'GitHub Release lookup transport failure' >&2; exit 1
fi
case "$status" in
  404) echo "Release $GITHUB_REF_NAME absent; proceed." ;;
  200) echo "Release $GITHUB_REF_NAME already exists; refusing overwrite." >&2; exit 1 ;;
  *) echo "GitHub Release lookup returned HTTP $status; refusing to infer absence." >&2; exit 1 ;;
esac
