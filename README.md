# NeoBank Data Platform

Учебная платформа данных розничного банка на синтетических данных.
Имитирует продакшн-контур: OLTP-источник → озеро (Parquet/MinIO) →
хранилище → витрины → BI. Ведётся по 52-недельному плану —
[docs/plan/roadmap.md](docs/plan/roadmap.md), прогресс — [docs/plan/PROGRESS.md](docs/plan/PROGRESS.md).

## Быстрый старт

```
git clone <repo>
cd neobank-data-platform
uv sync --all-extras --dev
uv run pre-commit install
make up
```

Поднимет Postgres (`:5432`), MinIO (`:9001` консоль), Metabase (`:3000`).

## Команды

- `make up` / `make down` — окружение
- `make lint` / `make fmt` — ruff + mypy
- `make test` — pytest
- `make psql` — консоль базы

## Статус

Неделя 1 (см. [docs/plan/weeks/week-01-guide.md](docs/plan/weeks/week-01-guide.md)) — инфраструктура и ИИ-контур готовы.
