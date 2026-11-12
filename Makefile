all: run

install:
		uv sync

run:
		uv run python3 -m src $(MAP)

visual:
		uv run python3 -m src $(MAP) --visual

debug:
		uv run -m pdb -m src $(MAP)

clean:
		rm -rf .mypy_cache
		find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +


lint:
		uv run flake8 . --exclude .venv
		uv run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
		uv run flake8 . --exclude .venv
		uv run mypy . --strict


.PHONY: all run visual install debug clean lint lint-strict
