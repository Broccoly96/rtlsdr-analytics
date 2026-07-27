.PHONY: install lint fmt test

install:
	pip install -e ".[dev]"

lint:
	ruff check app tests scripts migrations

fmt:
	ruff format app tests scripts migrations
	ruff check --fix app tests scripts migrations

test:
	pytest
