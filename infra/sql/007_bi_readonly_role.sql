-- Роль для BI-инструмента (Metabase).
--
-- Почему отдельная роль, а не ai_readonly и не postgres:
--
-- postgres — суперюзер. BI-инструмент, смотрящий в базу правами
-- суперюзера, может её изменить: достаточно одного native-запроса
-- с delete, набранного в окне SQL-редактора. Metabase по умолчанию
-- разрешает произвольный SQL всем, у кого есть доступ.
--
-- ai_readonly — другой принципал. Разные субъекты должны иметь разные
-- идентичности, даже если права совпадают: иначе в логах Postgres
-- невозможно отличить запрос ассистента от запроса дашборда, нельзя
-- отозвать доступ одному, не задев другого, и нельзя задать им разные
-- таймауты.

create role bi_readonly with login password 'bi_readonly_local_only';

grant connect on database neobank to bi_readonly;

grant usage on schema berka to bi_readonly;
grant usage on schema meta to bi_readonly;

grant select on all tables in schema berka to bi_readonly;
grant select on all tables in schema meta to bi_readonly;

alter default privileges in schema berka grant select on tables to bi_readonly;
alter default privileges in schema meta grant select on tables to bi_readonly;

-- PII в BI не нужны: дашборды отвечают на вопросы про портфель и
-- обороты, а не про конкретного Яна Новака. Персональные данные в BI
-- — это неконтролируемая точка утечки: любой, у кого есть ссылка на
-- дашборд, видит их, а выгрузка в CSV доступна в один клик.
revoke all on berka.client_pii from bi_readonly;

-- Дашборд с тяжёлым запросом не должен занимать соединение бесконечно.
-- Лимит выше, чем у ai_readonly (30s): агрегаты по 1 млн транзакций
-- бывают законно медленными, а разведочные запросы ассистента нет.
alter role bi_readonly set statement_timeout = '60s';
alter role bi_readonly set idle_in_transaction_session_timeout = '60s';
