-- OMOP procedure_occurrence: every fact whose concept is a procedure.
select
    event_id as procedure_occurrence_id,
    person_id,
    concept_id as procedure_concept_id,
    started_at::date as procedure_date,
    started_at::timestamp as procedure_datetime,
    ended_at::date as procedure_end_date,
    ended_at::timestamp as procedure_end_datetime,
    32817 as procedure_type_concept_id,   -- EHR
    null::int as modifier_concept_id,
    null::int as quantity,
    null::int as provider_id,
    visit_occurrence_id,
    null::int as visit_detail_id,
    code::varchar(50) as procedure_source_value,
    coalesce(source_concept_id, 0) as procedure_source_concept_id,
    null::varchar(50) as modifier_source_value
from {{ ref('int_event') }}
where omop_table = 'procedure_occurrence'
