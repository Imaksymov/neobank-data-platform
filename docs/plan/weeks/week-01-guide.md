# Неделя 1 — Репозиторий, окружение, ИИ-контур

**Цель недели:** `git clone` → `make up` → через 5 минут работающее окружение. Плюс зафиксированные правила работы с ассистентом.

**Не цель:** изучить Docker, освоить Terraform, разобраться в CI. Всё это инструменты, они осваиваются попутно и весь год.

---

## Что здесь требует практики, а что нет

Главное решение недели — не потратить время не туда.

| Инструмент | Отдельная практика | Почему |
|---|---|---|
| **Git** | **Да, 2 часа** | Единственное здесь, что требует мышечной памяти. Ассистент не спасёт от неудачного rebase на общей ветке, а спрашивать его в панике вы не будете. Плюс это язык, на котором с вами говорят на код-ревью весь год |
| Docker / compose | Нет | Проект и есть практика. Туториал «поднимите nginx» ничего не добавит |
| uv | Нет | Документация читается за 20 минут, дальше по ходу |
| pre-commit | Нет | Настроили один раз, дальше работает само |
| GitHub Actions | Нет | Копируете рабочий workflow, разбираетесь при первой поломке |
| Makefile | Нет | Нужны три конструкции из тридцати |
| CLAUDE.md / промпты | **Да, но иначе** | Практика здесь — не упражнения, а осознанное написание документа и его доработка по мере накопления ошибок ассистента |

Общий принцип на весь год: **отдельная практика оправдана только там, где ошибка дорогая и необратимая, а помощь ассистента приходит слишком поздно.** Git попадает под это (испорченная история, потерянная работа), остальное — нет.

---

## Где учить

**Git — обязательный минимум (2 ч)**
- [Learn Git Branching](https://learngitbranching.js.org/?locale=ru_RU) — интерактивный тренажёр, есть русский. Пройти разделы «Основы» и «Перемещаем работу» (rebase, cherry-pick). Это те самые 2 часа практики.
- [Conventional Commits](https://www.conventionalcommits.org/ru/v1.0.0/) — спецификация, читается за 10 минут.
- [Oh Shit, Git!?!](https://ohshitgit.com/) — держать в закладках, не читать сейчас.

Что должно остаться в голове после: чем `rebase` отличается от `merge` и когда какой уместен; как исправить последний коммит; как разрешить конфликт не паникуя; что такое интерактивный rebase.

**Остальное — только справка по ходу дела**
- [uv](https://docs.astral.sh/uv/) — раздел Getting Started
- [Docker Compose file reference](https://docs.docker.com/reference/compose-file/) — смотреть при написании, не читать целиком
- [pre-commit](https://pre-commit.com/) — раздел Quick start
- [Ruff](https://docs.astral.sh/ruff/) — конфигурация в `pyproject.toml`

**Что читать на неделе фоном (не про инструменты)**
Reis & Housley, *Fundamentals of Data Engineering* — предисловие и глава 1. Это задаёт рамку на весь год: что вообще входит в дата-инжиниринг и где в этом жизненном цикле находитесь вы.

---

## Расписание недели

### Суббота, утро, 3 часа — проектирование (D)

Ассистент закрыт. Это правило действует с первой недели.

**1 час — Git-тренажёр.** Learn Git Branching, разделы «Основы» и «Перемещаем работу».

**1 час — ADR-000 «Правила работы».** Самый важный артефакт недели. Пишете от руки, отвечая на вопросы:
- Что в этом проекте генерируется ассистентом, а что пишется руками?
- Что проверяется обязательно, даже если выглядит правильно?
- Где граница: в каком случае я откатываю сгенерированный код целиком, а не правлю?
- Как я пойму через месяц, что скатился в имитацию?

Не переписывайте формулировки из плана — сформулируйте своими. Документ, который вы не продумали сами, вы не будете соблюдать.

**1 час — структура проекта.** На бумаге: какие каталоги, что в каждом, почему именно так. Плюс решение по именованию: схемы, слои, префиксы моделей. Это ляжет в `CLAUDE.md`.

### Понедельник, 1,5 часа — каркас

1. Создать публичный репозиторий `neobank-data-platform`, лицензия MIT, `.gitignore` для Python.
2. `uv init`, зависимости.
3. Дерево каталогов, в каждом — `.gitkeep` и одна строка в `README.md` внутри каталога о его назначении.
4. `Makefile`.
5. Первый коммит по conventional commits, ветка `main` защищена от прямого пуша (Settings → Branches).

С этого момента — только через PR, включая свои собственные изменения.

### Вторник, 1,5 часа — инфраструктура

`docker-compose.yml`: Postgres, MinIO, Metabase, инициализация бакетов. Поднять, убедиться, что все три healthcheck зелёные.

Почти наверняка что-то не заведётся с первого раза — обычно healthcheck MinIO. **Это первое настоящее упражнение недели.** Диагностика: `docker compose ps` → `docker compose logs <сервис>` → `docker compose exec <сервис> sh` и проверка команды изнутри контейнера. Не гуглите готовый compose-файл, разберите причину.

### Среда, 1,5 часа — качество кода

`pre-commit` с ruff, ruff-format, mypy, sqlfluff, стандартные хуки. Настройка в `pyproject.toml` и `.sqlfluff`. Прогнать `pre-commit run --all-files`, довести до зелёного.

### Четверг, 1,5 часа — ИИ-контур

1. `CLAUDE.md` в корне.
2. `ai/prompts/` с тремя шаблонами.
3. Read-only роль в Postgres для ассистента + `statement_timeout`.
4. `docs/ai-failures.md` — завести с шаблоном записи.

### Воскресенье, 2 часа — закрытие (V)

1. `.github/workflows/ci.yml`, добиться зелёного прогона.
2. `README.md`: что это, зачем, как запустить, дорожная карта.
3. **Self-review PR.** Открыть diff и прочитать его глазами рецензента. Найти минимум три замечания к себе — они всегда есть.
4. Полная проверка: `git clone` в чистую папку → `make up` → всё поднялось.
5. Мерж, тег `week-01`.
6. Заметка на 5 строк: что не смог объяснить без подсказки.

---

## Готовые конфигурации

Инфраструктурный boilerplate копируйте не думая — он не несёт обучающей ценности. **`CLAUDE.md` и ADR-000 копировать нельзя**: это и есть содержательная часть недели.

### Структура

```
neobank-data-platform/
├── .github/workflows/ci.yml
├── ai/
│   ├── prompts/
│   └── README.md
├── docs/
│   ├── adr/000-ways-of-working.md
│   ├── ai-failures.md
│   └── backlog.md
├── infra/
│   ├── docker-compose.yml
│   └── sql/
├── ingestion/
├── transform/
├── orchestration/
├── quality/
├── ml/
├── tests/
├── CLAUDE.md
├── Makefile
├── pyproject.toml
├── .pre-commit-config.yaml
└── README.md
```

### `pyproject.toml`

```toml
[project]
name = "neobank-data-platform"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "polars>=1.0",
    "pyarrow>=17.0",
    "sqlalchemy>=2.0",
    "psycopg[binary]>=3.2",
    "pydantic-settings>=2.4",
    "structlog>=24.4",
    "typer>=0.12",
    "httpx>=0.27",
    "tenacity>=9.0",
]

[dependency-groups]
dev = ["pytest>=8.3", "pytest-cov>=5.0", "mypy>=1.11", "ruff>=0.6", "pre-commit>=3.8"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "TID", "PD", "RUF"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_unreachable = true

[tool.pytest.ini_options]
addopts = "-q --cov=ingestion --cov-report=term-missing"
testpaths = ["tests"]
```

### `infra/docker-compose.yml`

```yaml
name: neobank

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: neobank
      POSTGRES_USER: neobank
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-neobank}
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./sql:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U neobank -d neobank"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD:-minioadmin}
    ports: ["9000:9000", "9001:9001"]
    volumes:
      - miniodata:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5

  createbuckets:
    image: minio/mc:latest
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      mc alias set local http://minio:9000 $${MINIO_USER:-minioadmin} $${MINIO_PASSWORD:-minioadmin};
      mc mb --ignore-existing local/raw local/staging local/curated;
      exit 0;
      "

  metabase:
    image: metabase/metabase:latest
    ports: ["3000:3000"]
    volumes:
      - mbdata:/metabase-data
    environment:
      MB_DB_FILE: /metabase-data/metabase.db
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  pgdata:
  miniodata:
  mbdata:
```

Если healthcheck MinIO не проходит — в вашей версии образа может не быть `mc`. Альтернатива через встроенный эндпоинт:
```yaml
test: ["CMD-SHELL", "curl -fsS http://localhost:9000/minio/health/live || exit 1"]
```
Проверьте изнутри контейнера, какая команда доступна, прежде чем менять.

### `Makefile`

```makefile
.PHONY: help up down logs ps psql lint fmt test clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

up:  ## Поднять окружение
	docker compose -f infra/docker-compose.yml up -d
	@echo "Postgres :5432 | MinIO :9001 | Metabase :3000"

down:  ## Остановить
	docker compose -f infra/docker-compose.yml down

logs:  ## Логи (make logs s=postgres)
	docker compose -f infra/docker-compose.yml logs -f $(s)

ps:  ## Статус
	docker compose -f infra/docker-compose.yml ps

psql:  ## Консоль Postgres
	docker compose -f infra/docker-compose.yml exec postgres psql -U neobank -d neobank

lint:  ## Линтеры
	uv run ruff check .
	uv run mypy .

fmt:  ## Форматирование
	uv run ruff format .
	uv run ruff check --fix .

test:  ## Тесты
	uv run pytest

clean:  ## Удалить данные (осторожно)
	docker compose -f infra/docker-compose.yml down -v
```

### `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ["--maxkb=500"]
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, types-requests]

  - repo: https://github.com/sqlfluff/sqlfluff
    rev: 3.2.5
    hooks:
      - id: sqlfluff-lint
```

Установка: `uv run pre-commit install`. Версии хуков актуализируйте через `pre-commit autoupdate`.

### `.sqlfluff`

```ini
[sqlfluff]
dialect = postgres
templater = jinja
max_line_length = 120
exclude_rules = LT05, ST06

[sqlfluff:rules:capitalisation.keywords]
capitalisation_policy = lower

[sqlfluff:rules:capitalisation.identifiers]
extended_capitalisation_policy = lower
```

Строчные ключевые слова — соглашение экосистемы dbt. Если вам ближе `SELECT` капсом, решите сейчас и зафиксируйте, но менять на 20-й неделе будет больно.

### `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync --all-extras --dev

      - name: Lint
        run: |
          uv run ruff check .
          uv run ruff format --check .

      - name: Type check
        run: uv run mypy .

      - name: Tests
        run: uv run pytest
```

На первой неделе тестов ещё нет — добавьте `tests/test_smoke.py` с одним `assert True`, чтобы pytest не падал на пустой выборке. Уберёте на третьей неделе.

### `infra/sql/001_ai_readonly_role.sql`

Роль для ассистента. Выполняется автоматически при первом поднятии Postgres.

```sql
create role ai_readonly with login password 'ai_readonly_local_only';

grant connect on database neobank to ai_readonly;
grant usage on schema public to ai_readonly;
grant select on all tables in schema public to ai_readonly;

alter default privileges in schema public
    grant select on tables to ai_readonly;

-- защита от случайного тяжёлого запроса
alter role ai_readonly set statement_timeout = '30s';
alter role ai_readonly set idle_in_transaction_session_timeout = '60s';
```

Пароль здесь допустим только потому, что база локальная, синтетическая и не выходит за пределы вашей машины. Как только появится что-то настоящее — Secrets Manager.

---

## `CLAUDE.md` — каркас, который заполняете сами

Это конфигурация проекта для ассистента. Она будет расти весь год: каждая запись в журнале ошибок рано или поздно превращается в правило здесь.

```markdown
# Контекст проекта

## Что это
Платформа данных розничного банка на синтетических данных.
Учебный проект, имитирующий продакшн-контур: OLTP-источник → озеро →
хранилище → витрины → BI и ML.

## Домен
<Опишите своими словами: клиенты, счета, транзакции, кредиты, карты.
Ключевые сущности и их связи. 10–15 строк.>

## Архитектурные принципы
- Слоистость строгая: staging → intermediate → marts. Обратных ссылок нет.
- Staging не содержит бизнес-логики — только переименование, типы, дедупликация.
- Любая бизнес-метрика определена в одном месте и переиспользуется.
- Идемпотентность обязательна: повторный запуск не меняет результат.

## Соглашения
- Python: 3.12, полная типизация, ruff, строгий mypy.
- SQL: строчные ключевые слова, CTE вместо вложенных подзапросов,
  явные имена джойнов, никаких `select *` вне staging.
- Именование моделей: `stg_<источник>__<сущность>`, `int_<описание>`,
  `fct_<факт>`, `dim_<измерение>`.
- Деньги: `numeric`, никогда `float`. Даты: явные типы, UTC в хранении.
- Коммиты: conventional commits.

## Чего НЕ делать
- Не предлагать `pandas` там, где уместен `polars`.
- Не использовать `float` для денежных сумм.
- Не писать `except: pass` и не глотать исключения.
- Не обновлять состояние загрузки до подтверждения записи данных.
- Не генерировать тесты, не спросив, что считается корректным результатом.
- Не менять более одного слоя за раз.

## Как я работаю
Я сначала пишу спецификацию, потом прошу реализацию, потом проверяю сам.
Если задача сформулирована расплывчато — задай уточняющие вопросы,
а не угадывай. Если видишь неоднозначность в определении метрики —
останови и спроси.

## Известные ошибки
<Ссылка на docs/ai-failures.md. Пополняется по ходу.>
```

Раздел «Чего НЕ делать» на первой неделе короткий и во многом взят из чужого опыта. К 20-й неделе он станет вашим самым ценным разделом, потому что каждая строка будет оплачена собственным пойманным багом.

---

## `docs/ai-failures.md` — шаблон

```markdown
# Журнал ошибок ассистента

Каждая пойманная ошибка — одна запись. Ведётся с недели 1.

---

## AF-001 · YYYY-MM-DD · <короткое название>

**Контекст:** какая задача решалась
**Что было предложено:** фрагмент кода или суть решения
**Почему неверно:** конкретный механизм отказа, а не «плохо»
**Как обнаружил:** тест / чтение кода / расхождение цифр / прод
**Класс ошибки:** идемпотентность | типы и точность | границы окна |
семантика join | обработка NULL | время и таймзоны | глотание исключений | прочее
**Правило в CLAUDE.md:** добавлено / не требуется
```

Поле «класс ошибки» кажется избыточным на первой записи и становится главным на пятидесятой: именно из него на 27-й неделе вырастет таксономия.

---

## `ai/prompts/` — три шаблона

Промпты версионируются как код. На первой неделе достаточно трёх.

**`review-sql.md`** — ревью SQL:
```
Проверь этот SQL как рецензент, а не как автор.
Контекст проекта — в CLAUDE.md.

Ищи в порядке приоритета:
1. Размножение строк при join (fan-out)
2. Неверные границы оконных функций (ROWS vs RANGE)
3. Потерю строк на inner join там, где нужен left
4. Обработку NULL в агрегатах и сравнениях
5. Проблемы с типами и точностью денежных сумм
6. Расхождение с определениями метрик из глоссария

Для каждой находки: строка, механизм отказа, минимальный пример,
на котором это проявится. Не переписывай код целиком.
```

**`explain-and-quiz.md`** — сократический разбор:
```
Объясни <тема> для человека с 5 годами SQL в Oracle,
без опыта распределённых систем.
Затем задай мне 5 вопросов на понимание, по одному.
Оценивай ответы строго, указывай на пробелы, не подсказывай заранее.
```

**`critique-design.md`** — оппонирование:
```
Вот моя спецификация: <...>
Не реализуй её. Найди:
- 3 слабых места
- 1 сценарий, при котором решение сломается в продакшене
- 1 вопрос, на который я не ответил в спецификации
Решение приму я.
```

---

## Definition of Done

- [ ] `git clone` в чистую папку → `make up` → три сервиса зелёные за 5 минут
- [ ] `make lint` и `make test` проходят локально
- [ ] CI зелёный на PR
- [ ] `main` защищена, изменения только через PR
- [ ] `CLAUDE.md` написан своими словами, не скопирован
- [ ] ADR-000 отвечает на четыре вопроса из субботнего блока
- [ ] `docs/ai-failures.md` заведён
- [ ] Read-only роль работает: подключились ею и получили ошибку на `insert`
- [ ] README объясняет проект человеку, который видит его впервые
- [ ] Тег `week-01`

**Проверка «объясни вслепую»** (5 минут, без ассистента): чем `rebase` отличается от `merge` и почему нельзя делать rebase опубликованной ветки; зачем нужен healthcheck и что произойдёт без него; почему ассистент подключён read-only ролью, а не основной.

---

## Типичные способы потерять неделю

**Обустройство вместо работы.** Полдня на выбор темы для терминала и настройку шрифтов. Ограничение: инструментальные решения принимаются за 15 минут, дальше живёте с выбранным.

**Углубление в Docker.** «Раз уж взялся, изучу networking и multi-stage builds.» Не сейчас. В `docs/backlog.md` и дальше.

**Копирование `CLAUDE.md` из интернета.** Документ работает ровно настолько, насколько вы его продумали. Чужой файл будет игнорироваться вами же через месяц.

**Пропуск Git-тренажёра как «я это знаю».** Проверка простая: умеете сделать интерактивный rebase на пять коммитов, переставив два местами? Если нет — два часа окупятся к третьему месяцу.

---

## Настройка на неделю 2

Перед закрытием недели скачайте датасет Berka (PKDD'99) в `data/raw/` — он в `.gitignore`, но должен быть на диске. Бегло посмотрите на структуру файлов: восемь таблиц, разделитель `;`, кодировка не UTF-8. Это ваша вторая неделя.
