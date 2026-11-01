-- OMOP measurement: results with a value, such as lab tests and vital signs.
select
    event_id as measurement_id,
    person_id,
    concept_id as measurement_concept_id,
    started_at::date as measurement_date,
    started_at::timestamp as measurement_datetime,
    null::varchar(10) as measurement_time,
    32817 as measurement_type_concept_id,   -- EHR
    null::int as operator_concept_id,
    value_number as value_as_number,
    value_concept_id as value_as_concept_id,
    unit_concept_id,
    null::numeric as range_low,
    null::numeric as range_high,
    null::int as provider_id,
    visit_occurrence_id,
    null::int as visit_detail_id,
    code::varchar(50) as measurement_source_value,
    coalesce(source_concept_id, 0) as measurement_source_concept_id,
    value_unit::varchar(50) as unit_source_value,
    null::int as unit_source_concept_id,
    left(coalesce(value_code, value_text), 50)::varchar(50) as value_source_value,
    null::int as measurement_event_id,
    null::int as meas_event_field_concept_id
from {{ ref('int_event') }}
where omop_table = 'measurement'
