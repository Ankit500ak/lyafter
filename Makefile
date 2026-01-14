.PHONY: help up down logs test clean

help:
	@echo "Webhook API - here's what you can do:"
	@echo "  make up      - Start it"
	@echo "  make down    - Stop it"
	@echo "  make logs    - Watch logs"
	@echo "  make test    - Run tests"
	@echo "  make clean   - Delete containers"
	@echo "  make build   - Build the image"

up:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f api

test:
	python -m pytest tests/ -v

test-webhook:
	python -m pytest tests/test_webhook.py -v

test-messages:
	python -m pytest tests/test_messages.py -v

test-stats:
	python -m pytest tests/test_stats.py -v

build:
	docker compose build

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

shell:
	docker compose exec api bash

health:
	curl -sf http://localhost:8000/health/live && echo " - running" || echo "not running"
	curl -sf http://localhost:8000/health/ready && echo " - ready" || echo "not ready"
