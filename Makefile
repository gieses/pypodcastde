.DEFAULT_GOAL := help
UV ?= uv
RUN = $(UV) run --locked
ARGS ?=
VERSION = $(shell $(UV) version --short)
RELEASE_FILES = dist/pypodcastde-$(VERSION)-py3-none-any.whl dist/pypodcastde-$(VERSION).tar.gz

.PHONY: help setup lint format format-check test check hooks pre-commit build publish-check publish-test publish preview mine schedule

help:
	@echo "pypodcastde - developer and crawler commands"
	@echo "  make setup         Install locked runtime and development dependencies"
	@echo "  make check         Check lockfile, lint, formatting, and unit tests"
	@echo "  make lint          Check Python with Ruff"
	@echo "  make format        Apply safe lint fixes and format Python"
	@echo "  make format-check  Check formatting without changing files"
	@echo "  make test          Run the offline unit tests"
	@echo "  make hooks         Install the Git pre-commit hook in this checkout"
	@echo "  make pre-commit    Run hooks against all tracked files"
	@echo "  make build         Build the source distribution and wheel"
	@echo "  make publish-check Build and check the release without uploading"
	@echo "  make publish-test  Build and upload the current version to TestPyPI"
	@echo "  make publish       Build and upload the current version to PyPI"
	@echo "  make preview       Preview a crawl without downloading"
	@echo "  make mine          Download missing episodes"
	@echo "  make schedule      Run the daily crawler in the foreground"
	@echo "  Example: make preview ARGS=--force"

setup:
	$(UV) sync --locked

lint:
	$(RUN) ruff check pypodcastde tests

format:
	$(RUN) ruff check --fix pypodcastde tests
	$(RUN) ruff format pypodcastde tests

format-check:
	$(RUN) ruff format --check pypodcastde tests

test:
	$(RUN) pytest -q --cov=pypodcastde

check: lint format-check test
	$(UV) lock --check

hooks:
	$(RUN) pre-commit install

pre-commit:
	$(RUN) pre-commit run --all-files

build:
	$(UV) lock --check
	$(UV) build

publish-check: build
	$(UV) publish --dry-run --trusted-publishing never $(RELEASE_FILES)

publish-test: build
	$(UV) publish --publish-url https://test.pypi.org/legacy/ $(RELEASE_FILES)

publish: build
	$(UV) publish --publish-url https://upload.pypi.org/legacy/ $(RELEASE_FILES)

preview:
	$(RUN) pypodcastde mine --try $(ARGS)

mine schedule:
	$(RUN) pypodcastde $@ $(ARGS)
