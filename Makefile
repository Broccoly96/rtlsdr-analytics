.PHONY: install lint fmt test

install:
	pip install -e ".[dev]"

lint:
	ruff check app tests scripts

fmt:
	ruff format app tests scripts
	ruff check --fix app tests scripts

test:
	pytest
