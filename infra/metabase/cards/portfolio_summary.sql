-- Портфель в цифрах: базовые объёмы для верхней строки дашборда.
select
    (select count(*) from berka.client) as "Клиентов",
    (select count(*) from berka.account) as "Счетов",
    (select count(*) from berka.loan) as "Кредитов выдано",
    (
        select count(*) from berka.loan
        where status in ('C', 'D')
    ) as "Действующих",
    (select count(*) from berka.card) as "Карт"
