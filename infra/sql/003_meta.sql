-- Служебные метаданные платформы.
-- Отдельная схема, а не внутри berka: berka обязана зеркалить реальный
-- источник, а наша бухгалтерия в банковской OLTP не лежала бы.

create schema if not exists meta;

comment on schema meta is 'Служебные метаданные платформы, не часть источника';

-- --------------------------------------------------------------------
-- date_shift: параметр проекции исторических данных на современные даты
-- --------------------------------------------------------------------
create table meta.date_shift (
    source_name text primary key,
    shift_days int not null,
    source_min date not null,
    source_max date not null,
    shifted_min date,
    shifted_max date,
    applied_at timestamptz,
    rationale text
);

comment on table meta.date_shift is 'Сдвиг дат источника: параметр, факт применения и обоснование';
comment on column meta.date_shift.shift_days is 'Постоянный сдвиг в днях, кратный 7 — иначе сместятся дни недели';
comment on column meta.date_shift.shifted_min is 'Фактический минимум после загрузки, заполняется 02_transform.sql';
comment on column meta.date_shift.applied_at is 'NULL означает, что сдвиг объявлен, но ещё не применён';

insert into meta.date_shift (source_name, shift_days, source_min, source_max, rationale)
values (
    'berka',
    10150,
    '1993-01-01',
    '1998-12-31',
    'Кратен 7 (1450 недель ровно), поэтому дни недели сохраняются: 1993-01-01 пятница -> 2020-10-16 пятница. '
    'Банковские данные имеют недельную структуру (операции в рабочие дни, коммунальные платежи по графику), '
    'и сдвиг на некратное 7 показал бы массовые операции в выходные. '
    'Величина выбрана так, чтобы максимум (2026-10-15) не уезжал в будущее: данные с датами впереди current_date '
    'тихо ломают инкрементальную загрузку — watermark прыгает вперёд, и следующие запуски перестают видеть строки.'
);

-- --------------------------------------------------------------------
-- Сдвиг как функция, а не константа в четырёх местах: определение
-- живёт в одном месте, а транзформация остаётся читаемой.
-- stable, а не immutable: читает таблицу.
-- --------------------------------------------------------------------
create function meta.shift_date(d date) returns date
language sql
stable
as $$
select d + (select shift_days from meta.date_shift where source_name = 'berka')
$$;

comment on function meta.shift_date(date) is 'Проецирует историческую дату источника на современную по meta.date_shift';
