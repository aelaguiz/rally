.DEFAULT_GOAL := help

UV ?= uv
PYTHON ?= python

UV_RUN := $(UV) run $(PYTHON)
DOCTRINE_SOURCE ?= git+https://github.com/aelaguiz/doctrine.git@v1.0.1

.PHONY: help setup test tests verify check release-prepare release-tag release-draft release-publish

help:
	@printf '%s\n' \
		'make setup             Sync Rally dev dependencies.' \
		'make tests             Run the Rally unit suite.' \
		'make test              Alias for make tests.' \
		'make verify            Run the release proof path.' \
		'make check             Alias for make verify.' \
		'make release-prepare   Validate release inputs and print the release worksheet.' \
		'make release-tag       Create and push one signed annotated public release tag.' \
		'make release-draft     Create one GitHub draft release from an existing pushed tag.' \
		'make release-publish   Publish one reviewed GitHub draft release and wait for publish.yml.'

setup:
	$(UV) sync --dev

tests:
	$(UV) run pytest tests/unit -q

test: tests

verify:
	$(UV) run python tools/sync_bundled_assets.py --check
	$(UV) run pytest tests/unit/test_release_flow.py -q
	$(UV) run pytest tests/unit -q
	$(UV) build
	RALLY_TEST_DOCTRINE_SOURCE=$(DOCTRINE_SOURCE) $(UV) run pytest tests/integration/test_packaged_install.py -q

check: verify

release-prepare:
	@test -n "$(RELEASE)" || { printf '%s\n' 'RELEASE is required.'; exit 2; }
	@test -n "$(CLASS)" || { printf '%s\n' 'CLASS is required.'; exit 2; }
	@test -n "$(CHANNEL)" || { printf '%s\n' 'CHANNEL is required.'; exit 2; }
	$(UV_RUN) -m rally.release_flow prepare --release "$(RELEASE)" --class "$(CLASS)" --channel "$(CHANNEL)"

release-tag:
	@test -n "$(RELEASE)" || { printf '%s\n' 'RELEASE is required.'; exit 2; }
	@test -n "$(CHANNEL)" || { printf '%s\n' 'CHANNEL is required.'; exit 2; }
	$(UV_RUN) -m rally.release_flow tag --release "$(RELEASE)" --channel "$(CHANNEL)"

release-draft:
	@test -n "$(RELEASE)" || { printf '%s\n' 'RELEASE is required.'; exit 2; }
	@test -n "$(CHANNEL)" || { printf '%s\n' 'CHANNEL is required.'; exit 2; }
	$(UV_RUN) -m rally.release_flow draft --release "$(RELEASE)" --channel "$(CHANNEL)" --previous-tag "$(or $(PREVIOUS_TAG),auto)"

release-publish:
	@test -n "$(RELEASE)" || { printf '%s\n' 'RELEASE is required.'; exit 2; }
	$(UV_RUN) -m rally.release_flow publish --release "$(RELEASE)"
