#!/usr/bin/env bash
# Загрузка Berka из data/raw в схему berka.
#
# Файлы передаются в psql через stdin (\copy, клиентская команда),
# а не читаются сервером (COPY) — поэтому монтировать data/ в
# контейнер не нужно, и тот же скрипт работал бы против managed-базы,
# где серверный COPY из локального файла невозможен.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# Массив, а не строка: путь к репозиторию может содержать пробелы,
# и при подстановке строки shell разбил бы её на слова.
COMPOSE=(docker compose -f "${REPO_ROOT}/infra/docker-compose.yml")
PGUSER="${POSTGRES_USER:-postgres}"
PGDB="${POSTGRES_DB:-neobank}"
RAW_DIR="${REPO_ROOT}/data/raw"
SQL_DIR="${REPO_ROOT}/ingestion/berka"

psql_run() {
    "${COMPOSE[@]}" exec -T postgres psql -U "$PGUSER" -d "$PGDB" -v ON_ERROR_STOP=1 -q "$@"
}

for f in district client account disp card loan order trans; do
    [ -f "${RAW_DIR}/${f}.csv" ] || { echo "Нет файла ${RAW_DIR}/${f}.csv" >&2; exit 1; }
done

echo "1/4 landing-таблицы"
psql_run < "${SQL_DIR}/01_landing.sql"

echo "2/4 \\copy файлов"
for f in district client account disp card loan order trans; do
    printf '  %-9s' "$f"
    psql_run -c "\\copy berka_landing.\"${f}\" from stdin with (format csv, header true, delimiter ';')" \
        < "${RAW_DIR}/${f}.csv"
done

echo "3/4 преобразование в типизированный источник"
psql_run < "${SQL_DIR}/02_transform.sql"

# PII генерируются после клиентов: генератор читает client_id,
# birth_number и район из уже загруженных таблиц.
echo "4/4 синтетические PII"
(cd "$REPO_ROOT" && uv run python ingestion/berka/generate_pii.py)

echo
echo "Строк загружено:"
psql_run -c "
select 'district' as tbl, count(*) from berka.district
union all select 'client',     count(*) from berka.client
union all select 'client_pii', count(*) from berka.client_pii
union all select 'account',    count(*) from berka.account
union all select 'disp',       count(*) from berka.disp
union all select 'card',       count(*) from berka.card
union all select 'loan',       count(*) from berka.loan
union all select 'order',      count(*) from berka.\"order\"
union all select 'trans',      count(*) from berka.trans;
"
