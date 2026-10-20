"""Генерация синтетических PII для клиентов Berka.

В источнике персональных данных нет — датасет анонимизирован. Эти данные
нужны, чтобы отрабатывать маскирование по ролям и удаление клиента.

Детерминирован: фиксированный seed плюс обход клиентов строго по
возрастанию client_id. Порядок важен не меньше seed'а — Faker выдаёт
значения последовательно, и без order by одному и тому же клиенту при
разных запусках достались бы разные имена.
"""

import os
import unicodedata
from typing import Final

import psycopg
from faker import Faker

SEED: Final[int] = 19930101
LOCALE: Final[str] = "cs_CZ"

# example.com зарезервирован RFC 2606 и гарантированно не существует.
# Реальный домен в синтетических данных однажды привёл бы к отправке
# писем настоящим людям.
EMAIL_DOMAIN: Final[str] = "example.com"

SELECT_CLIENTS: Final[str] = """
select c.client_id, c.birth_number, d.a2
from berka.client as c
inner join berka.district as d on c.district_id = d.a1
order by c.client_id
"""

INSERT_PII: Final[str] = """
insert into berka.client_pii
    (client_id, sex, first_name, last_name, street, city, phone, email, id_document)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

PiiRow = tuple[int, str, str, str, str, str, str, str, str]


def dsn() -> str:
    """Строка подключения из переменных окружения с дефолтами compose."""
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    database = os.environ.get("POSTGRES_DB", "neobank")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def sex_from_birth_number(birth_number: str) -> str:
    """Пол из чешского birth_number: к месяцу женщин прибавлено 50.

    Проверено на данных: цифры месяца образуют две полосы, 01-12 и
    51-62, промежуточных значений нет ни одного.
    """
    month = int(birth_number[2:4])
    return "F" if month > 50 else "M"


def ascii_fold(text: str) -> str:
    """Убирает диакритику: Beneš -> Benes. Нужно для адреса почты."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def build_row(fake: Faker, client_id: int, birth_number: str, city: str) -> PiiRow:
    """Собирает одну запись PII, согласованную с полом и районом клиента."""
    sex = sex_from_birth_number(birth_number)

    # Чешские фамилии гендерно-зависимы: Jelínek / Jelínková. Faker это
    # учитывает, если спрашивать мужской и женский варианты раздельно.
    if sex == "F":
        first_name = fake.first_name_female()
        last_name = fake.last_name_female()
    else:
        first_name = fake.first_name_male()
        last_name = fake.last_name_male()

    local_part = f"{ascii_fold(first_name)}.{ascii_fold(last_name)}".lower()

    return (
        client_id,
        sex,
        first_name,
        last_name,
        fake.street_address().replace("\n", ", "),
        city,
        fake.phone_number(),
        f"{local_part}@{EMAIL_DOMAIN}",
        fake.numerify("#########"),
    )


def main() -> None:
    fake = Faker(LOCALE)
    Faker.seed(SEED)

    with psycopg.connect(dsn()) as conn:
        clients = conn.execute(SELECT_CLIENTS).fetchall()
        rows = [
            build_row(fake, int(client_id), str(birth_number), str(city))
            for client_id, birth_number, city in clients
        ]

        with conn.cursor() as cur:
            cur.execute("truncate table berka.client_pii")
            cur.executemany(INSERT_PII, rows)

        conn.commit()

    print(f"PII сгенерированы: {len(rows)} клиентов, seed {SEED}, локаль {LOCALE}")


if __name__ == "__main__":
    main()
