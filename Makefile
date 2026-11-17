SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := build
.DELETE_ON_ERROR:
PYTHON ?= python3
CURL ?= curl
GAMS_RELEASE_API ?= https://api.github.com/repos/kkgams/gams/releases/latest
UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)
DOCS_PORT ?= 8080
WIKI_VERSION := v1.4.0
WIKI_REPOSITORY := https://github.com/justgook/wiki
WIKI_MAKEFILE := build.nosync/wiki-$(WIKI_VERSION).mk
WIKI_ENGINE := $(abspath build.nosync/wiki-$(WIKI_VERSION))
export TMPDIR := $(abspath build.nosync/tmp)
export PYTHONPYCACHEPREFIX := $(abspath build.nosync/pycache)
SOURCE := plugins/tile-detect.comp
WIT := $(shell find $(SOURCE)/wit -type f)
WIT_DIRS := $(shell find $(SOURCE)/wit -type d)
LEGAL_DIRS := $(shell find LICENSES third_party -type d)
LEGAL := LICENSE NOTICE LICENSING.md $(sort $(shell find LICENSES third_party -type f \( -iname '*license*' -o -name 'W3C-Community-CLA.html' -o -path 'LICENSES/*' \)))
ARTIFACT := build.nosync/plugin.tile-detect.wasm
.PHONY: test all build package check clean open docs serve-docs validate-docs
all: build
build: $(ARTIFACT)

build.nosync/tmp:
	@mkdir -p "$@"

MODULE_INPUTS := $(shell find $(SOURCE) -maxdepth 1 -type f \( -name '*.go' -o -name 'go.mod' -o -name 'go.sum' \))
MODULE_FILES := $(patsubst $(SOURCE)/%,build.nosync/tile-detect/%,$(MODULE_INPUTS))
SDK := $(shell find sdk -type f)
SDK_DIRS := $(shell find sdk -type d)
export GOCACHE := $(abspath build.nosync/go-cache)
export GOMODCACHE := $(abspath build.nosync/go-modules)
export TINYGOCACHE := $(abspath build.nosync/tinygo-cache)
export GOTOOLCHAIN := local
export GOFLAGS := -modcacherw

$(MODULE_FILES) &: $(MODULE_INPUTS) $(SOURCE) Makefile | build.nosync/tmp
	mkdir -p build.nosync/tile-detect
	rm -f build.nosync/tile-detect/*.go build.nosync/tile-detect/go.mod build.nosync/tile-detect/go.sum
	cp $(MODULE_INPUTS) build.nosync/tile-detect/

build.nosync/package.wasm: $(WIT) $(WIT_DIRS) Makefile flake.nix flake.lock | build.nosync/tmp
	wasm-tools component wit $(SOURCE)/wit --wasm -o "$@"

BINDINGS := build.nosync/tile-detect/internal/gams/tile-detect/tile-detect-plugin/tile-detect-plugin.wit.go \
	build.nosync/tile-detect/internal/gams/tile-detect/tile-detect/abi.go \
	build.nosync/tile-detect/internal/gams/tile-detect/tile-detect/empty.s \
	build.nosync/tile-detect/internal/gams/tile-detect/tile-detect/tile-detect.exports.go \
	build.nosync/tile-detect/internal/gams/tile-detect/tile-detect/tile-detect.wasm.go \
	build.nosync/tile-detect/internal/gams/tile-detect/tile-detect/tile-detect.wit.go \
	build.nosync/tile-detect/internal/wasi/cli/environment/empty.s \
	build.nosync/tile-detect/internal/wasi/cli/environment/environment.wasm.go \
	build.nosync/tile-detect/internal/wasi/cli/environment/environment.wit.go \
	build.nosync/tile-detect/internal/wasi/cli/exit/empty.s \
	build.nosync/tile-detect/internal/wasi/cli/exit/exit.wasm.go \
	build.nosync/tile-detect/internal/wasi/cli/exit/exit.wit.go \
	build.nosync/tile-detect/internal/wasi/cli/stderr/empty.s \
	build.nosync/tile-detect/internal/wasi/cli/stderr/stderr.wasm.go \
	build.nosync/tile-detect/internal/wasi/cli/stderr/stderr.wit.go \
	build.nosync/tile-detect/internal/wasi/cli/stdin/empty.s \
	build.nosync/tile-detect/internal/wasi/cli/stdin/stdin.wasm.go \
	build.nosync/tile-detect/internal/wasi/cli/stdin/stdin.wit.go \
	build.nosync/tile-detect/internal/wasi/cli/stdout/empty.s \
	build.nosync/tile-detect/internal/wasi/cli/stdout/stdout.wasm.go \
	build.nosync/tile-detect/internal/wasi/cli/stdout/stdout.wit.go \
	build.nosync/tile-detect/internal/wasi/cli/terminal-input/empty.s \
	build.nosync/tile-detect/internal/wasi/cli/terminal-input/terminal-input.wasm.go \
	build.nosync/tile-detect/internal/wasi/cli/terminal-input/terminal-input.wit.go \
	build.nosync/tile-detect/internal/wasi/cli/terminal-output/empty.s \
	build.nosync/tile-detect/internal/wasi/cli/terminal-output/terminal-output.wasm.go \
	build.nosync/tile-detect/internal/wasi/cli/terminal-output/terminal-output.wit.go \
	build.nosync/tile-detect/internal/wasi/cli/terminal-stderr/empty.s \
	build.nosync/tile-detect/internal/wasi/cli/terminal-stderr/terminal-stderr.wasm.go \
	build.nosync/tile-detect/internal/wasi/cli/terminal-stderr/terminal-stderr.wit.go \
	build.nosync/tile-detect/internal/wasi/cli/terminal-stdin/empty.s \
	build.nosync/tile-detect/internal/wasi/cli/terminal-stdin/terminal-stdin.wasm.go \
	build.nosync/tile-detect/internal/wasi/cli/terminal-stdin/terminal-stdin.wit.go \
	build.nosync/tile-detect/internal/wasi/cli/terminal-stdout/empty.s \
	build.nosync/tile-detect/internal/wasi/cli/terminal-stdout/terminal-stdout.wasm.go \
	build.nosync/tile-detect/internal/wasi/cli/terminal-stdout/terminal-stdout.wit.go \
	build.nosync/tile-detect/internal/wasi/clocks/monotonic-clock/empty.s \
	build.nosync/tile-detect/internal/wasi/clocks/monotonic-clock/monotonic-clock.wasm.go \
	build.nosync/tile-detect/internal/wasi/clocks/monotonic-clock/monotonic-clock.wit.go \
	build.nosync/tile-detect/internal/wasi/clocks/wall-clock/empty.s \
	build.nosync/tile-detect/internal/wasi/clocks/wall-clock/wall-clock.wasm.go \
	build.nosync/tile-detect/internal/wasi/clocks/wall-clock/wall-clock.wit.go \
	build.nosync/tile-detect/internal/wasi/filesystem/preopens/empty.s \
	build.nosync/tile-detect/internal/wasi/filesystem/preopens/preopens.wasm.go \
	build.nosync/tile-detect/internal/wasi/filesystem/preopens/preopens.wit.go \
	build.nosync/tile-detect/internal/wasi/filesystem/types/abi.go \
	build.nosync/tile-detect/internal/wasi/filesystem/types/empty.s \
	build.nosync/tile-detect/internal/wasi/filesystem/types/types.wasm.go \
	build.nosync/tile-detect/internal/wasi/filesystem/types/types.wit.go \
	build.nosync/tile-detect/internal/wasi/io/error/empty.s \
	build.nosync/tile-detect/internal/wasi/io/error/error.wasm.go \
	build.nosync/tile-detect/internal/wasi/io/error/error.wit.go \
	build.nosync/tile-detect/internal/wasi/io/poll/empty.s \
	build.nosync/tile-detect/internal/wasi/io/poll/poll.wasm.go \
	build.nosync/tile-detect/internal/wasi/io/poll/poll.wit.go \
	build.nosync/tile-detect/internal/wasi/io/streams/empty.s \
	build.nosync/tile-detect/internal/wasi/io/streams/streams.wasm.go \
	build.nosync/tile-detect/internal/wasi/io/streams/streams.wit.go \
	build.nosync/tile-detect/internal/wasi/random/insecure-seed/empty.s \
	build.nosync/tile-detect/internal/wasi/random/insecure-seed/insecure-seed.wasm.go \
	build.nosync/tile-detect/internal/wasi/random/insecure-seed/insecure-seed.wit.go \
	build.nosync/tile-detect/internal/wasi/random/insecure/empty.s \
	build.nosync/tile-detect/internal/wasi/random/insecure/insecure.wasm.go \
	build.nosync/tile-detect/internal/wasi/random/insecure/insecure.wit.go \
	build.nosync/tile-detect/internal/wasi/random/random/empty.s \
	build.nosync/tile-detect/internal/wasi/random/random/random.wasm.go \
	build.nosync/tile-detect/internal/wasi/random/random/random.wit.go \
	build.nosync/tile-detect/internal/wasi/sockets/instance-network/empty.s \
	build.nosync/tile-detect/internal/wasi/sockets/instance-network/instance-network.wasm.go \
	build.nosync/tile-detect/internal/wasi/sockets/instance-network/instance-network.wit.go \
	build.nosync/tile-detect/internal/wasi/sockets/ip-name-lookup/abi.go \
	build.nosync/tile-detect/internal/wasi/sockets/ip-name-lookup/empty.s \
	build.nosync/tile-detect/internal/wasi/sockets/ip-name-lookup/ip-name-lookup.wasm.go \
	build.nosync/tile-detect/internal/wasi/sockets/ip-name-lookup/ip-name-lookup.wit.go \
	build.nosync/tile-detect/internal/wasi/sockets/network/abi.go \
	build.nosync/tile-detect/internal/wasi/sockets/network/empty.s \
	build.nosync/tile-detect/internal/wasi/sockets/network/network.wasm.go \
	build.nosync/tile-detect/internal/wasi/sockets/network/network.wit.go \
	build.nosync/tile-detect/internal/wasi/sockets/tcp-create-socket/empty.s \
	build.nosync/tile-detect/internal/wasi/sockets/tcp-create-socket/tcp-create-socket.wasm.go \
	build.nosync/tile-detect/internal/wasi/sockets/tcp-create-socket/tcp-create-socket.wit.go \
	build.nosync/tile-detect/internal/wasi/sockets/tcp/abi.go \
	build.nosync/tile-detect/internal/wasi/sockets/tcp/empty.s \
	build.nosync/tile-detect/internal/wasi/sockets/tcp/tcp.wasm.go \
	build.nosync/tile-detect/internal/wasi/sockets/tcp/tcp.wit.go \
	build.nosync/tile-detect/internal/wasi/sockets/udp-create-socket/empty.s \
	build.nosync/tile-detect/internal/wasi/sockets/udp-create-socket/udp-create-socket.wasm.go \
	build.nosync/tile-detect/internal/wasi/sockets/udp-create-socket/udp-create-socket.wit.go \
	build.nosync/tile-detect/internal/wasi/sockets/udp/abi.go \
	build.nosync/tile-detect/internal/wasi/sockets/udp/empty.s \
	build.nosync/tile-detect/internal/wasi/sockets/udp/udp.wasm.go \
	build.nosync/tile-detect/internal/wasi/sockets/udp/udp.wit.go

$(BINDINGS) &: build.nosync/package.wasm $(MODULE_FILES) Makefile
	cd build.nosync/tile-detect && go tool wit-bindgen-go generate --world tile-detect-plugin --out internal ../package.wasm

$(ARTIFACT): $(MODULE_FILES) $(BINDINGS) $(SDK) $(SDK_DIRS) $(SOURCE) $(LEGAL) $(LEGAL_DIRS) scripts/wasm-notices.py Makefile flake.nix flake.lock
	cd build.nosync/tile-detect && tinygo build -target=wasip2 -opt=2 -no-debug -o ../plugin.tile-detect.wasm --wit-package ../package.wasm --wit-world tile-detect-plugin main.go
	wasm-tools strip -a "$@" -o "$@.stripped"
	mv "$@.stripped" "$@"
	$(PYTHON) scripts/wasm-notices.py embed "$@" --license LICENSE --notice NOTICE
	wasm-tools validate "$@"

test: $(MODULE_FILES) $(BINDINGS)
	cd build.nosync/tile-detect && go test ./...
	cd sdk && go test ./...

check: | build.nosync/tmp
	$(PYTHON) -c 'import ast; from pathlib import Path; [ast.parse(p.read_text()) for p in Path("scripts").glob("*.py")]'

package: build.nosync/SHA256SUMS $(ARTIFACT) build.nosync/LICENSES.zip

build.nosync/LICENSES.zip: $(LEGAL) $(LEGAL_DIRS) Makefile | build.nosync/tmp
	rm -f "$@"
	zip -q -X "$@" $(LEGAL)

build.nosync/SHA256SUMS: $(ARTIFACT) build.nosync/LICENSES.zip
	cd build.nosync && shasum -a 256 plugin.tile-detect.wasm LICENSES.zip > SHA256SUMS

clean:
	$(PYTHON) -B scripts/clean.py

# Retain an existing app; never update it implicitly.
tools/gams.app: | build.nosync/tmp
	@test "$(UNAME_S)" = Darwin && test "$(UNAME_M)" = arm64 || \
		{ echo 'GAMS release download requires macOS Apple Silicon' >&2; exit 1; }
	@test ! -e tools/gams-release-notices || \
		{ echo 'tools/gams-release-notices already exists; move it aside before reinstalling GAMS' >&2; exit 1; }
	@mkdir -p tools
	@set -eu; stage=$$(mktemp -d "$(TMPDIR)/gams-download.XXXXXX"); \
		trap 'rm -rf "$$stage"' EXIT; \
		$(CURL) --fail --location --silent --show-error "$(GAMS_RELEASE_API)" --output "$$stage/release.json"; \
		url=$$($(PYTHON) -c 'import json, sys; release = json.load(open(sys.argv[1])); assets = [a for a in release["assets"] if a["name"].startswith("GAMS-") and a["name"].endswith("-macos-aarch64.zip")]; assert len(assets) == 1, "Expected exactly one GAMS macOS Apple Silicon ZIP asset"; print(assets[0]["browser_download_url"])' "$$stage/release.json"); \
		$(CURL) --fail --location --silent --show-error "$$url" --output "$$stage/gams.zip"; \
		unzip -q "$$stage/gams.zip" -d "$$stage/unpacked"; \
		test -f "$$stage/unpacked/GAMS.app/Contents/Info.plist"; \
		test -x "$$stage/unpacked/GAMS.app/Contents/MacOS/gams"; \
		mv "$$stage/unpacked/GAMS.app" "$$stage/GAMS.app"; \
		mv "$$stage/unpacked" tools/gams-release-notices; \
		mv "$$stage/GAMS.app" "$@"

open: build tools/gams.app
	GAMS_APP_CWD="$(CURDIR)" GAMS_CONFIG="gams.json" ./tools/gams.app/Contents/MacOS/gams

$(WIKI_MAKEFILE): | build.nosync/tmp
	$(CURL) --fail --location --retry 3 "$(WIKI_REPOSITORY)/raw/$(WIKI_VERSION)/Makefile" -o "$@.tmp"
	mv "$@.tmp" "$@"

docs serve-docs validate-docs: $(WIKI_MAKEFILE) | build.nosync/tmp
	$(MAKE) -f "$(WIKI_MAKEFILE)" "$(if $(filter docs,$@),build,$(patsubst %-docs,%,$@))" WIKI_REPOSITORY="$(WIKI_REPOSITORY)" WIKI_VERSION="$(WIKI_VERSION)" WIKI_ENGINE="$(WIKI_ENGINE)" WIKI_SOURCE="$(abspath docs)" WIKI_OUTPUT="$(abspath build.nosync/site)" PORT="$(DOCS_PORT)"
