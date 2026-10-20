-- Источник Berka (PKDD'99): имитация OLTP-системы банка.
-- Имена колонок и коды сохранены как в источнике; переименование
-- и разбор закодированных полей — работа staging-слоя.
-- Схема данных описана в docs/models/source_berka.md.

create schema if not exists berka;

comment on schema berka is 'OLTP-источник: чешский банк, 1993-1998 (PKDD''99 Berka)';

-- --------------------------------------------------------------------
-- district: районы. Колонки A1-A16 — как в оригинальном датасете.
-- --------------------------------------------------------------------
create table berka.district (
    a1 int primary key,
    a2 text not null,
    a3 text not null,
    a4 int not null,
    a5 int not null,
    a6 int not null,
    a7 int not null,
    a8 int not null,
    a9 int not null,
    a10 numeric(5, 1) not null,
    a11 int not null,
    a12 numeric(5, 2),
    a13 numeric(5, 2) not null,
    a14 int not null,
    a15 int,
    a16 int not null
);

comment on column berka.district.a1 is 'код района (PK)';
comment on column berka.district.a2 is 'название района';
comment on column berka.district.a3 is 'регион';
comment on column berka.district.a4 is 'число жителей';
comment on column berka.district.a5 is 'муниципалитетов < 499 жителей';
comment on column berka.district.a6 is 'муниципалитетов 500-1999 жителей';
comment on column berka.district.a7 is 'муниципалитетов 2000-9999 жителей';
comment on column berka.district.a8 is 'муниципалитетов > 10000 жителей';
comment on column berka.district.a9 is 'число городов';
comment on column berka.district.a10 is 'доля городского населения, %';
comment on column berka.district.a11 is 'средняя зарплата';
comment on column berka.district.a12 is 'безработица 1995, % (NULL для района 69)';
comment on column berka.district.a13 is 'безработица 1996, %';
comment on column berka.district.a14 is 'предпринимателей на 1000 жителей';
comment on column berka.district.a15 is 'преступлений 1995 (NULL для района 69)';
comment on column berka.district.a16 is 'преступлений 1996';

-- --------------------------------------------------------------------
-- client: клиенты
-- --------------------------------------------------------------------
create table berka.client (
    client_id int primary key,
    birth_number char(6) not null,
    district_id int not null references berka.district (a1)
);

comment on column berka.client.birth_number is 'YYMMDD, к месяцу женщин прибавлено 50; разбор — в staging';

create index on berka.client (district_id);

-- --------------------------------------------------------------------
-- account: счета
-- --------------------------------------------------------------------
create table berka.account (
    account_id int primary key,
    district_id int not null references berka.district (a1),
    frequency text not null,
    date date not null
);

comment on column berka.account.district_id is 'район отделения, не клиента';
comment on column berka.account.frequency is 'POPLATEK MESICNE | POPLATEK TYDNE | POPLATEK PO OBRATU';
comment on column berka.account.date is 'дата открытия счёта';

create index on berka.account (district_id);

-- --------------------------------------------------------------------
-- disp: диспозиции — связь клиента и счёта с ролью
-- --------------------------------------------------------------------
create table berka.disp (
    disp_id int primary key,
    client_id int not null references berka.client (client_id),
    account_id int not null references berka.account (account_id),
    type text not null
);

comment on table berka.disp is 'Связь клиент-счёт. OWNER — владелец (ровно один на счёт), DISPONENT — распорядитель без владения (0..1 на счёт)';
comment on column berka.disp.type is 'OWNER | DISPONENT';

create index on berka.disp (client_id);
create index on berka.disp (account_id);

-- --------------------------------------------------------------------
-- card: карты, выпускаются к диспозиции
-- --------------------------------------------------------------------
create table berka.card (
    card_id int primary key,
    disp_id int not null unique references berka.disp (disp_id),
    type text not null,
    issued date not null
);

comment on column berka.card.type is 'classic | gold | junior';
comment on column berka.card.issued is 'в источнике формат "YYMMDD 00:00:00", время всегда нулевое';

-- --------------------------------------------------------------------
-- loan: кредиты, не более одного на счёт
-- --------------------------------------------------------------------
create table berka.loan (
    loan_id int primary key,
    account_id int not null unique references berka.account (account_id),
    date date not null,
    amount numeric(12, 2) not null,
    duration int not null,
    payments numeric(12, 2) not null,
    status char(1) not null
);

comment on column berka.loan.date is 'дата выдачи';
comment on column berka.loan.duration is 'срок, месяцев';
comment on column berka.loan.payments is 'ежемесячный платёж';
comment on column berka.loan.status is 'A — погашен без проблем | B — закрыт, не погашен | C — действует, просрочки нет | D — действует, есть просрочка';

-- --------------------------------------------------------------------
-- order: постоянные платёжные поручения
-- order — зарезервированное слово, имя источника сохранено намеренно
-- --------------------------------------------------------------------
create table berka."order" (
    order_id int primary key,
    account_id int not null references berka.account (account_id),
    bank_to char(2) not null,
    account_to text not null,
    amount numeric(12, 2) not null,
    k_symbol text
);

comment on column berka."order".account_to is 'счёт получателя во внешнем банке';
comment on column berka."order".k_symbol is 'назначение: POJISTNE | SIPO | LEASING | UVER';

create index on berka."order" (account_id);

-- --------------------------------------------------------------------
-- trans: движения по счетам
-- --------------------------------------------------------------------
create table berka.trans (
    trans_id int primary key,
    account_id int not null references berka.account (account_id),
    date date not null,
    type text not null,
    operation text,
    amount numeric(12, 2) not null,
    balance numeric(12, 2) not null,
    k_symbol text,
    bank char(2),
    account text
);

comment on column berka.trans.type is 'PRIJEM — приход | VYDAJ — расход | VYBER — снятие';
comment on column berka.trans.operation is 'VKLAD | VYBER | PREVOD NA UCET | PREVOD Z UCTU | VYBER KARTOU; NULL допустим';
comment on column berka.trans.balance is 'остаток после операции — эталон для сверки';
comment on column berka.trans.bank is 'банк контрагента, NULL для внутренних операций';

create index on berka.trans (account_id, date);
create index on berka.trans (date);
