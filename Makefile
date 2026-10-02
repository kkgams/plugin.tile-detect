SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.PHONY: all build test clean release-candidate verify-candidate
all: build
build:
	python3 scripts/build.py build
test:
	python3 scripts/build.py test
release-candidate: test
	bash scripts/check-licensing-digests.sh
	python3 scripts/candidate.py stage
verify-candidate:
	bash scripts/check-licensing-digests.sh
	python3 scripts/candidate.py verify
clean:
	rm -rf build dist node_modules
	find plugins -type d -name internal -prune -exec rm -rf '{}' +
