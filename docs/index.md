---
title: plugin.tile-detect
description: Detect and extract image tiles.
status: reference
---

# plugin.tile-detect

A [GAMS](https://github.com/kkgams/gams) WASM plugin for detecting and extracting tiles from images.

| Unit | Source / artifact | Original work |
| --- | --- | --- |
| Tile detection and extraction | `plugins/tile-detect.comp/main.go` / `plugin.tile-detect.wasm` | GAMS |

## API

`plugins/tile-detect.comp/wit/package.wit` defines `gams:tile-detect/tile-detect@1.0.0`: `detect-size` to estimate tile dimensions/confidence, `extract` for tile banks/maps, `export-tileset` for image bytes/dimensions and `to-tilemap` for layered maps. The `tile-detect-plugin` world uses Host-provided WASI imports.

## Development

Use `nix develop` (or direnv) for pinned Go 1.25, TinyGo, wasm-tools and documentation tools. No sibling checkout is required.

| Command | Purpose |
| --- | --- |
| `make build` | Compile and validate the component with embedded notices. |
| `make package` | Prepare `build.nosync/plugin.tile-detect.wasm`, `LICENSES.zip` and `SHA256SUMS` incrementally. |
| `make test` | Run the native Go package checks and existing SDK tilemap tests. |
| `make check` | Check Python tooling syntax; native tests are separate from WASM runtime coverage. |
| `make open` | Build and open this local Project in the released macOS Apple Silicon Host. |
| `make docs` | Build the wiki to `build.nosync/site`. |
| `make serve-docs` | Preview the wiki; `DOCS_PORT` defaults to 8080. |
| `make validate-docs` | Validate wiki content. |
| `make clean` | Remove all of `build.nosync/`, `tools/` and `gams_modules/`, including unmarked contents; refuse tracked files and symlinks before deleting anything. |

The local Project browses files with pinned published Units; it is not an image tile editor or runtime test. Downloads preserve accompanying notices and existing Host tools. Packaging does not verify native Host/API behavior.
