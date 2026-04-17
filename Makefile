.DEFAULT_GOAL := help

UV ?= uv
PYTHON ?= python

UV_RUN := $(UV) run $(PYTHON)

.PHONY: help setup emit test tests build-dist verify-package-wheel verify-package-sdist verify-package verify check release-prepare release-tag release-draft release-publish

help:
	@printf '%s\n' \
		'make setup                 Sync Rally dev dependencies.' \
		'make emit                  Compile the checked-in Rally flow and skill bundles.' \
		'make tests                 Run the Rally unit suite.' \
		'make test                  Alias for make tests.' \
		'make build-dist            Build the Rally wheel and sdist.' \
		'make verify-package        Run the built-package smoke proof for wheel and sdist.' \
		'make verify                Run the broader Rally release proof path.' \
		'make check                 Alias for make verify.' \
		'make release-prepare       Validate release inputs and print the release worksheet.' \
		'make release-tag           Create and push one signed annotated public release tag.' \
		'make release-draft         Create one GitHub draft release from an existing pushed tag.' \
		'make release-publish       Publish one reviewed GitHub draft release and wait for publish.yml.'

setup:
	$(UV) sync --dev

emit:
	$(UV_RUN) -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo
	$(UV_RUN) -m doctrine.emit_skill --pyproject pyproject.toml --target rally-kernel --target rally-memory --target demo-git

tests: emit
	$(UV) run pytest tests/unit -q

test: tests

build-dist:
	rm -rf dist
	$(UV) build

verify-package-wheel: build-dist
	$(UV_RUN) -m rally._package_release smoke --artifact-type wheel

verify-package-sdist: build-dist
	$(UV_RUN) -m rally._package_release smoke --artifact-type sdist

verify-package: build-dist
	$(UV_RUN) -m rally._package_release smoke --artifact-type wheel
	$(UV_RUN) -m rally._package_release smoke --artifact-type sdist

verify: emit
	$(UV) run pytest tests/unit/test_package_release.py -q
	$(UV) run pytest tests/unit/test_release_flow.py -q
	$(UV) run pytest tests/unit -q
	$(MAKE) verify-package
	$(UV) run pytest tests/integration/test_packaged_install.py -q

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
