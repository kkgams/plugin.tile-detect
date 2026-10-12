# plugin.tile-detect

GAMS WASM Project Unit for detecting and extracting tiles from image data.
Distribution and WIT interface versions are independent.

## API

Exports `gams:tile-detect/tile-detect@1.0.0` through `tile-detect-plugin`.
`detect-size` estimates tile dimensions/confidence. `extract` produces a tile
bank and tile map, `export-tileset` returns image bytes and dimensions, and
`to-tilemap` converts extraction results to the shared layered map shape.
The Host supplies the world's WASI imports.

The contract is in `plugins/tile-detect.comp/wit/package.wit`.
Plugin Manager resolves imports; distribution filenames do not rename WIT identities.

## Build and test

All source/build inputs are owned by this repository; no sibling checkout is
required for its supported build/test commands. Use the pinned Nix environment:

```sh
nix develop --command make build
nix develop --command make test
```

Output: `dist/plugin.tile-detect.wasm`. Install it as
`plugins/tile-detect.comp.wasm` in an external GAMS Project. Configure that Project separately.

The flake and lockfiles pin the toolchain. Network access may be required to
fetch tools/modules. `.envrc` supports `direnv allow`.

`make test` runs offline integrity/publication regression tests, builds the
components, validates WASM, extracts WIT, and checks the exact input inventory.
It also runs native Go unit tests for the plugin and its local SDK. Native Go
tests are not WASM runtime tests; there is no standalone component runtime E2E.

## Licensing and releases

GAMS-authored contributions are Apache-2.0. Third-party code retains its own
terms; see `LICENSING.md`, `THIRD-PARTY-REVIEW.md`, and `LICENSES/`.
Source inventory and notice evidence are checked before candidate packaging.
Changed inputs require refreshed exact evidence; checksum consistency alone is
not legal approval. On 2026-10-12 the owner confirmed licensing/checksums were
already prepared and removed pending manual checksum, license, and hosted-review
approvals for 0.2.1, authorizing local commits and annotated tags. This does not
claim hosted tests, final artifact review, or missing runtime coverage passed.

Distribution is through GitHub Releases, not npm or OCI. Before publishing:

1. Preserve exact source and third-party evidence. Manual reviews were waived
   by the owner for 0.2.1; hosted execution remains unverified, not a manual
   approval blocker. Enforced build and publication checks still must pass.
2. Set repository-scoped `LICENSE_SHA256` and `NOTICE_SHA256` Actions variables
   to the exact authorized texts. Local rehearsal uses
   `APPROVED_LICENSE_SHA256` and `APPROVED_NOTICE_SHA256`.
3. Push the authorized `release` branch and verify its hosted candidate. Without
   approved digests, branch checks do not distribute a candidate. Manual release
   workflow dispatch verifies but does not publish.
4. Tag the authorized release-branch commit as `v<version.txt>`. Never reuse or
   move a published or failed tag. Publication requires immutable-release policy,
   canonical repository/version identity, exact artifacts and checksums, embedded
   notices, and complete readable legal assets. An existing release blocks creation.

The publication workflow rehearses a private draft's bytes before publication
and checks the anonymous public bytes afterward. Keep LICENSE, NOTICE, evidence,
review documents, and applicable LICENSES with distributed artifacts. See the
repository's release workflow and scripts for the enforced gates.
