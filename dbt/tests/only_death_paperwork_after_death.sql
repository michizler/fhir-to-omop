-- The one thing allowed after a death is the certificate, recorded at a paperwork visit up to a few weeks later.
-- Any other event after death would mean records joined to the wrong person.
select e.event_id, e.source_table, e.code, e.code_display, e.started_at, d.death_date
from {{ ref('int_event') }} e
join {{ ref('death') }} d using (person_id)
where e.started_at::date > d.death_date
  and e.code <> '69453-9'
