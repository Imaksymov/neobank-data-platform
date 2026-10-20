-- Права ai_readonly на схемы, созданные после 001_ai_readonly_role.sql.
--
-- Почему отдельным файлом: в 001 роль получила select только на public,
-- где данных нет. Схемы berka и meta появились позже, и роль их не
-- видела — то есть read-only доступ ассистента формально существовал,
-- а фактически не работал. Проверка недели 1 это пропустила: она
-- подтверждала запрет на запись, но не возможность чтения.

grant usage on schema berka to ai_readonly;
grant usage on schema meta to ai_readonly;

grant select on all tables in schema berka to ai_readonly;
grant select on all tables in schema meta to ai_readonly;

-- Таблицы, созданные в этих схемах впредь, тоже должны быть видны —
-- иначе права снова «протухнут» при добавлении таблицы.
alter default privileges in schema berka grant select on tables to ai_readonly;
alter default privileges in schema meta grant select on tables to ai_readonly;
