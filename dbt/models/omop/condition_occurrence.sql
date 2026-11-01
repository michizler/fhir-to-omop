-- OMOP condition_occurrence: every fact whose concept is a condition, whatever FHIR called it.
select
    event_id as condition_occurrence_id,
    person_id,
    concept_id as condition_concept_id,
    started_at::date as condition_start_date,
    started_at::timestamp as condition_start_datetime,
    ended_at::date as condition_end_date,
    ended_at::timestamp as condition_end_datetime,
    32817 as condition_type_concept_id,   -- EHR
    null::int as condition_status_concept_id,
    null::varchar(20) as stop_reason,
    null::int as provider_id,
    visit_occurrence_id,
    null::int as visit_detail_id,
    code::varchar(50) as condition_source_value,
    coalesce(source_concept_id, 0) as condition_source_concept_id,
    null::varchar(50) as condition_status_source_value
from {{ ref('int_event') }}
where omop_table = 'condition_occurrence'
