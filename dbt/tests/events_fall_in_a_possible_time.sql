-- No visit may start before the person was born. Dates that fail point at a broken join rather than odd data.
select v.visit_occurrence_id, v.visit_start_date, p.birth_datetime
from {{ ref('visit_occurrence') }} v
join {{ ref('person') }} p using (person_id)
where v.visit_start_date < p.birth_datetime::date
