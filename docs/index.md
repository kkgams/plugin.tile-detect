---
title: Development
status: reference
---

# plugin.tile-detect development

## Build and test

Use the repository's pinned Nix environment from its root:

```sh
nix develop
make build
make test
```

Local output is under `dist/`. See the repository README for the exported WIT
contract, test coverage and existing release requirements. Runtime, packaging,
licensing evidence and version-tag publication policies are unchanged.

## Open the local Project

On macOS Apple Silicon, from the same development shell:

```sh
make open
```

This builds the local component artifacts, downloads the released Host into
ignored `tools/gams.app` if absent, and explicitly selects this repository's
`gams.json` using `GAMS_APP_CWD`. No neighboring checkout is needed. Downloaded
Host notices remain in `tools/gams-release-notices`; an existing app is never
updated implicitly. No Gatekeeper bypass is performed.

The released file browser is the initial View; the local component is loaded
for Host integration. This Project does not provide a custom UI for this plugin
or claim to exercise its API. Use the repository tests for the documented checks.

The Project pins published filesystem/layout components, shell UI Services,
theme and Views. First launch requires network access for those dependencies;
Host-installed Units stay in ignored `gams_modules/`.

## Documentation

```sh
make serve-docs DOCS_PORT=8080
make validate-docs
make docs
```

These targets use pinned `justgook/wiki` v1.4.0. `DOCS_PORT` is independent of
application ports. `make docs` writes the portable site to `build/site/`;
`make build-docs` remains an alias. Downloads and generated output stay under
ignored `build/`. Every push to `release` builds through `make docs` and deploys
GitHub Pages independently of version-tag releases.
