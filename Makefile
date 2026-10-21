.PHONY: help up down logs ps psql load metabase lint fmt test clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

up:  ## Поднять окружение
	docker compose -f infra/docker-compose.yml up -d
	@echo "Postgres :5432 | MinIO :9001 | Metabase :3000"

down:  ## Остановить (тома сохраняются)
	docker compose -f infra/docker-compose.yml down

logs:  ## Логи (make logs s=postgres)
	docker compose -f infra/docker-compose.yml logs -f $(s)

ps:  ## Статус
	docker compose -f infra/docker-compose.yml ps

psql:  ## Консоль Postgres
	docker compose -f infra/docker-compose.yml exec postgres psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-neobank}

load:  ## Загрузить Berka из data/raw в схему berka (+ синтетические PII)
	./ingestion/berka/load.sh

metabase:  ## Настроить Metabase и собрать дашборд
	uv run python infra/metabase/setup.py

lint:  ## Линтеры
	uv run ruff check .
	uv run mypy .

fmt:  ## Форматирование
	uv run ruff format .
	uv run ruff check --fix .

test:  ## Тесты
	uv run pytest

clean:  ## Удалить контейнеры и тома (данные пропадут)
	docker compose -f infra/docker-compose.yml down -v
