-- Топ районов по числу клиентов.
-- district_id у клиента — его собственный район; у счёта это район
-- отделения, и они не обязаны совпадать.
select
    d.a2 as "Район",
    d.a3 as "Регион",
    count(*) as "Клиентов",
    d.a11 as "Средняя зарплата"
from berka.client as c
inner join berka.district as d on c.district_id = d.a1
group by d.a2, d.a3, d.a11
order by count(*) desc
limit 10
