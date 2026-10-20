-- Перенос из landing в типизированный источник.
-- Идемпотентно: повторный запуск даёт тот же результат, не дубли.
--
-- Алиасы в select формально не нужны: при insert ... select имена
-- колонок берутся из списка целевой таблицы, а не из запроса. Они
-- здесь для читаемости — видно, какое выражение питает какую колонку.

-- Один truncate на все таблицы сразу: взаимные FK при этом не мешают,
-- тогда как восемь отдельных пришлось бы упорядочивать вручную.
-- client_pii включена, хотя заполняется не здесь, а generate_pii.py:
-- она ссылается на client внешним ключом, и без неё Postgres откажется
-- усекать client вообще.
truncate table berka.trans, berka."order", berka.loan, berka.card, berka.disp, berka.account, berka.client_pii, berka.client, berka.district;

-- Даты в источнике — YYMMDD. Век задаём явной склейкой '19' || ...,
-- а не маской 'YYMMDD': Postgres трактует YY 00-69 как 2000-е, 70-99
-- как 1900-е (проверено на этой базе). Для дат операций 93-98 маска
-- сработала бы верно, но правило зависит от данных, а не от схемы:
-- тот же birth_number с годами 11-69 она молча отправила бы в 2011-2069.
-- Явный век не зависит от диапазона вообще.
--
-- Поверх разбора даты применяется meta.shift_date() — проекция
-- 1993-1998 на современные даты. Сдвиг постоянный и кратный 7, поэтому
-- все интервалы и вся относительная хронология сохраняются, а дни
-- недели не смещаются. Параметр и обоснование — в meta.date_shift.
-- Сдвиг применяется при загрузке, а не UPDATE после: так он
-- идемпотентен по построению и не раздувает таблицу на 1 млн строк.

insert into berka.district
select
    a1::int,
    a2,
    a3,
    a4::int,
    a5::int,
    a6::int,
    a7::int,
    a8::int,
    a9::int,
    a10::numeric,
    a11::int,
    nullif(a12, '?')::numeric as a12,   -- район 69 (Jesenik): нет данных за 1995
    a13::numeric,
    a14::int,
    nullif(a15, '?')::int as a15,       -- то же
    a16::int
from berka_landing.district;

insert into berka.client
select
    client_id::int,
    birth_number,
    district_id::int
from berka_landing.client;

insert into berka.account
select
    account_id::int,
    district_id::int,
    frequency,
    meta.shift_date(to_date('19' || date, 'YYYYMMDD')) as date
from berka_landing.account;

insert into berka.disp
select
    disp_id::int,
    client_id::int,
    account_id::int,
    type
from berka_landing.disp;

insert into berka.card
select
    card_id::int,
    disp_id::int,
    type,
    meta.shift_date(to_date('19' || left(issued, 6), 'YYYYMMDD')) as issued  -- "931107 00:00:00"
from berka_landing.card;

insert into berka.loan
select
    loan_id::int,
    account_id::int,
    meta.shift_date(to_date('19' || date, 'YYYYMMDD')) as date,
    amount::numeric,
    duration::int,
    payments::numeric,
    status
from berka_landing.loan;

insert into berka."order"
select
    order_id::int,
    account_id::int,
    bank_to,
    account_to,
    amount::numeric,
    nullif(trim(k_symbol), '') as k_symbol
from berka_landing."order";

-- В trans пустые значения оформлены непоследовательно: где-то "",
-- где-то " " (пробел), где-то поле пустое без кавычек. Приводим всё
-- к NULL единообразно, иначе в витринах получим три разных "ничего".
insert into berka.trans
select
    trans_id::int,
    account_id::int,
    meta.shift_date(to_date('19' || date, 'YYYYMMDD')) as date,
    type,
    nullif(trim(operation), '') as operation,
    amount::numeric,
    balance::numeric,
    nullif(trim(k_symbol), '') as k_symbol,
    nullif(trim(bank), '') as bank,
    nullif(trim(account), '') as account
from berka_landing.trans;

-- Фиксируем факт применения: что получилось на самом деле, а не что
-- было задумано. Расхождение shifted_min с source_min + shift_days
-- означало бы, что сдвиг применён не ко всем колонкам.
update meta.date_shift
set
    shifted_min = (
        select min(d) from (
            select min(date) as d from berka.account
            union all
            select min(date) from berka.loan
            union all
            select min(issued) from berka.card
            union all
            select min(date) from berka.trans
        ) as s
    ),
    shifted_max = (
        select max(d) from (
            select max(date) as d from berka.account
            union all
            select max(date) from berka.loan
            union all
            select max(issued) from berka.card
            union all
            select max(date) from berka.trans
        ) as s
    ),
    applied_at = now()
where source_name = 'berka';

drop schema berka_landing cascade;
