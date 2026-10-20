-- Промежуточные таблицы для приёма CSV как есть: все колонки text,
-- никаких преобразований и ограничений. Задача этого слоя — чтобы
-- загрузка не могла упасть на типах, а разбор происходил дальше,
-- явным SQL, который можно прочитать и проверить.
-- Схема удаляется в конце 02_transform.sql.

drop schema if exists berka_landing cascade;
create schema berka_landing;

create unlogged table berka_landing.district (
    a1 text, a2 text, a3 text, a4 text, a5 text, a6 text, a7 text, a8 text,
    a9 text, a10 text, a11 text, a12 text, a13 text, a14 text, a15 text, a16 text
);

create unlogged table berka_landing.client (
    client_id text, birth_number text, district_id text
);

create unlogged table berka_landing.account (
    account_id text, district_id text, frequency text, date text
);

create unlogged table berka_landing.disp (
    disp_id text, client_id text, account_id text, type text
);

create unlogged table berka_landing.card (
    card_id text, disp_id text, type text, issued text
);

create unlogged table berka_landing.loan (
    loan_id text, account_id text, date text, amount text,
    duration text, payments text, status text
);

create unlogged table berka_landing."order" (
    order_id text, account_id text, bank_to text, account_to text,
    amount text, k_symbol text
);

create unlogged table berka_landing.trans (
    trans_id text, account_id text, date text, type text, operation text,
    amount text, balance text, k_symbol text, bank text, account text
);
