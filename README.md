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

Дальше нужны данные. Датасет Berka (PKDD'99) в репозиторий не входит —
положите восемь `.csv` в `data/raw/` (источники в
[docs/plan/context.md](docs/plan/context.md)), затем:

```
make load      # схема berka + синтетические PII
make metabase  # настройка Metabase и дашборд
```

## Команды

- `make up` / `make down` — окружение
- `make load` — загрузка источника из `data/raw/`
- `make metabase` — провижининг Metabase и дашборда
- `make lint` / `make fmt` — ruff + mypy
- `make test` — pytest
- `make psql` — консоль базы

## Данные

Схема источника и все его особенности —
[docs/models/source_berka.md](docs/models/source_berka.md).

Даты сдвинуты на современные (`meta.date_shift`), персональные данные
синтетические (Faker, фиксированный seed).

Роли доступа: `ai_readonly` для ассистента и `bi_readonly` для Metabase —
обе только на чтение и обе **без доступа к `berka.client_pii`**.

## Статус

Недели 1–2 (см. [docs/plan/PROGRESS.md](docs/plan/PROGRESS.md)) —
окружение, ИИ-контур, источник данных.
