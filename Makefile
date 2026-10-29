all: run

install:
	uv sync

run:
	uv run python3 -m src

debug:
	uv run -m pdb -m src

clean:
	rm -rf -R mypy_cache __pycache__

lint:
        uv run flake8 .
        uv run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
        uv run flake8 .
        uv run mypy . --strict


.PHONY: all run install debug clean lint lint-strict
