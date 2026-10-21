-- Операции и оборот по месяцам.
-- Даты здесь уже сдвинутые (meta.date_shift), поэтому ряд
-- заканчивается несколько дней назад, а не в 1998 году.
select
    date_trunc('month', date)::date as "Месяц",
    count(*) as "Операций",
    sum(amount) as "Оборот"
from berka.trans
group by date_trunc('month', date)
order by date_trunc('month', date)
