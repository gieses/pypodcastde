.DEFAULT_GOAL := help
UV ?= uv
RUN = $(UV) run --locked
ARGS ?=

.PHONY: help setup lint format format-check test check hooks pre-commit build preview mine schedule

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
	$(RUN) python -m unittest discover -s tests

check: lint format-check test
	$(UV) lock --check

hooks:
	$(RUN) pre-commit install

pre-commit:
	$(RUN) pre-commit run --all-files

build:
	$(UV) lock --check
	$(UV) build

preview:
	$(RUN) pypodcastde mine --try $(ARGS)

mine schedule:
	$(RUN) pypodcastde $@ $(ARGS)
