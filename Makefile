.PHONY: test lint deploy

test:
	uv run pytest -v

lint:
	uv run ruff check .
	uv run mypy .

deploy: lint test
	docker compose up --build -d
