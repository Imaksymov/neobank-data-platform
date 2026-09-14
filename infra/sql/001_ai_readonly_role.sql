create role ai_readonly with login password 'ai_readonly_local_only';

grant connect on database neobank to ai_readonly;
grant usage on schema public to ai_readonly;
grant select on all tables in schema public to ai_readonly;

alter default privileges in schema public
grant select on tables to ai_readonly;

-- защита от случайного тяжёлого запроса
alter role ai_readonly set statement_timeout = '30s';
alter role ai_readonly set idle_in_transaction_session_timeout = '60s';
