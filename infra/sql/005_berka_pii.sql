-- Синтетические персональные данные клиентов.
--
-- В Berka персональных данных нет: датасет анонимизирован для
-- исследований, клиент — это id, birth_number и район. PII нужны,
-- чтобы отрабатывать маскирование по ролям и удаление клиента
-- («право на забвение»), поэтому генерируются Faker'ом.
--
-- Отдельная таблица, а не колонки в berka.client, по двум причинам:
-- сохраняется проверяемое свойство «berka зеркалит файлы источника»
-- (на нём построена сверка контрольными суммами), и отделение PII от
-- операционных данных — реальный банковский паттерн, при котором
-- доступ отзывается на уровне таблицы, а не отдельных колонок.

create table berka.client_pii (
    client_id int primary key references berka.client (client_id),
    sex char(1) not null,
    first_name text not null,
    last_name text not null,
    street text not null,
    city text not null,
    phone text not null,
    email text not null,
    id_document char(9) not null,
    constraint client_pii_sex_check check (sex in ('M', 'F'))
);

comment on table berka.client_pii is 'Синтетические PII, сгенерированы Faker (cs_CZ) с фиксированным seed';
comment on column berka.client_pii.sex is 'Выведен из birth_number при генерации; эталон для проверки разбора в staging';
comment on column berka.client_pii.last_name is 'Чешские фамилии гендерно-зависимы: мужская Jelínek, женская Jelínková';
comment on column berka.client_pii.city is 'Название района клиента (district.a2): чешские районы названы по главному городу';
comment on column berka.client_pii.id_document is 'Номер удостоверения личности, 9 цифр';

create index on berka.client_pii (last_name, first_name);
