# Standalone GAMS plugin

See `component.json` for distribution artifacts and unchanged WIT worlds.
All source/build inputs live here; no sibling repositories or original checkout
are consulted. Native SDK helper copies are limited to the pure-Go packages used
by these plugins. Generated bindings and binaries are not extraction inputs.

```
nix develop --command make test
nix develop --command make build
```

The lockfile pins Nixpkgs, Odin db0cd7963, WASI SDK 33, wasm-tools 1.248.0 and
wit-bindgen 0.57.1. Nixpkgs supplies Go 1.25/TinyGo; Go sums lock modules and
package-lock locks jco test tooling. `.envrc` supports `direnv allow` locally.
Network access may be needed to acquire pinned tools/modules.

`make test` validates the real built components. Go plugins run native source
unit tests; Markov runs XML/MJIR compiler tests. Pack, random and SQL additionally
run jco-transpiled component runtime assertions. Other plugins currently have
static validation only. Original tests remain in source for reference; tests that
invoke cmd/app or a sibling MarkovJunior checkout are NOT standalone tests and
are NOT run/claimed. See PREPARATION.md for blockers.

Markov additionally produces a deterministic versioned tooling ZIP retaining the
XML compiler, CLI, resource XMLs, documentation, compiler tests and historical
parity tooling. The ZIP is not a fake WASM artifact or claimed complete parity
runner; historical parity requires further host/reference extraction.

## Publishing (owner operated)

GAMS-authored source is Apache-2.0. Upstream source headers are retained verbatim;
THIRD-PARTY-SOURCE.json binds review inputs. NOTICE is an inventory awaiting the
separate source-bound legal audit, not legal approval. Final candidate/tag gates
require that audit's NOTICE-EVIDENCE.json, THIRD-PARTY-REVIEW.md, LICENSING.md and
LICENSES/ closure; unresolved permission blockers fail closed. Legal texts and
evidence are included in WASM release assets (including LICENSES.zip), and all
are retained inside Markov's compiler/tooling ZIP. Review toolchain-linked
runtime/adapter terms too before approving digests. No binary distribution is
approved by preparation.

After the legal audit, set repository-scoped Actions variables LICENSE_SHA256 and
NOTICE_SHA256 to exact lowercase SHA-256 digests of reviewed texts. A local
candidate uses APPROVED_LICENSE_SHA256 and APPROVED_NOTICE_SHA256. Changes to
source evidence require renewed review/update of THIRD-PARTY-SOURCE.json.

Push the owner-reviewed `release` branch and inspect the exact hosted candidate;
branch verification without digests uploads nothing. Rehearse release.yml by
manual dispatch on `release` (verifies, never publishes). Only then tag that exact
commit as v<version.txt>. Never move/reuse a published or failed tag.

Tag jobs require canonical kkgams repository, matching version and current release
branch head, both approved legal digests, exact complete artifacts, embedded WASM
notices and checksum verification. Publication refuses existing GitHub Releases.
GitHub Release is the only configured distribution channel (no OCI publication).
No preparation command creates Git repositories/remotes, pushes or tags.
