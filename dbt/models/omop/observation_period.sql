-- OMOP observation_period: the span in which each person's records exist, from first event to last. Researchers rely
-- on it to know when a missing record means nothing happened, so every event must fall inside it.
with spans as (
    select person_id, visit_start_date as d0, visit_end_date as d1 from {{ ref('visit_occurrence') }}
    union all
    select person_id, started_at::date, coalesce(ended_at, started_at)::date from {{ ref('int_event') }}
)

select
    person_id as observation_period_id,
    person_id,
    min(d0) as observation_period_start_date,
    max(d1) as observation_period_end_date,
    32817 as period_type_concept_id   -- EHR
from spans
group by person_id
