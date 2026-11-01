-- OMOP observation: clinical facts that are not conditions, procedures, drugs or measurements, such as social history.
select
    event_id as observation_id,
    person_id,
    concept_id as observation_concept_id,
    started_at::date as observation_date,
    started_at::timestamp as observation_datetime,
    32817 as observation_type_concept_id,   -- EHR
    value_number as value_as_number,
    left(value_text, 60)::varchar(60) as value_as_string,
    value_concept_id as value_as_concept_id,
    null::int as qualifier_concept_id,
    unit_concept_id,
    null::int as provider_id,
    visit_occurrence_id,
    null::int as visit_detail_id,
    code::varchar(50) as observation_source_value,
    coalesce(source_concept_id, 0) as observation_source_concept_id,
    value_unit::varchar(50) as unit_source_value,
    null::varchar(50) as qualifier_source_value,
    left(coalesce(value_code, value_text), 50)::varchar(50) as value_source_value,
    null::int as observation_event_id,
    null::int as obs_event_field_concept_id
from {{ ref('int_event') }}
where omop_table = 'observation'
