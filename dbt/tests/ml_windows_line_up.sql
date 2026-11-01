-- Last year's outcome and this year's look-back count the same visits, so they must agree for anyone in both years.
-- A mismatch would mean a window is off by a day, which is how future data leaks into features.
select a.person_id, a.index_year, a.emergency_next_year, b.er_visits_1y
from {{ ref('ml_patient_year') }} a
join {{ ref('ml_patient_year') }} b on b.person_id = a.person_id and b.index_year = a.index_year + 1
where (a.emergency_next_year = 1) <> (b.er_visits_1y > 0)
