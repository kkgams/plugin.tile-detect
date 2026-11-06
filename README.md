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
`plugins/tile-detect.comp.wasm` in an external GAMS Project. A local development Project is also included.

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
Changed inputs require separately authorized evidence refreshes; source snapshot
verification remains strict and is not refreshed by release tooling.

Distribution is through GitHub Releases, not npm or OCI. Pushing a matching
`v<version.txt>` tag authorizes publication from that commit; no approval digest
variables or required publication branch are used. Manual workflow dispatch
verifies without publishing. Build/tests, canonical repository and tag/version
identity, legal texts and embedded notices, evidence/source inventory, artifact
checksums, candidate integrity, and no-overwrite checks must pass. Never reuse
or move a published or failed tag. An existing release blocks creation.

Enable immutable releases in the repository settings before publication. The
automatic GitHub token is sufficient; no administrative settings API or extra
policy token is used. Public release verification requires `immutable: true`.

The publication workflow rehearses a private draft's bytes before publication
and checks the anonymous public bytes afterward. Keep LICENSE, NOTICE, evidence,
review documents, and applicable LICENSES with distributed artifacts. See the
repository's release workflow and scripts for the enforced gates.

## Local Project and documentation

Run `nix develop --command make open` on macOS Apple Silicon to build local
artifacts and open this repository's `gams.json` with the downloaded released
Host. No sibling checkout is required; `tools/` and `gams_modules/` are ignored.
The existing Host is retained, with release notices kept alongside it.

Use `make serve-docs` (`DOCS_PORT` overrides 8080), `make validate-docs` and
`make docs` for the pinned wiki. The site is built into `build/site/`; pushes to
`release` publish it through GitHub Pages, independently of version tags.
See [development documentation](docs/index.md) for Project behavior and checks.
