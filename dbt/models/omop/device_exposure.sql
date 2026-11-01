-- OMOP device_exposure: the few procedures whose concept is a device.
select
    event_id as device_exposure_id,
    person_id,
    concept_id as device_concept_id,
    started_at::date as device_exposure_start_date,
    started_at::timestamp as device_exposure_start_datetime,
    ended_at::date as device_exposure_end_date,
    ended_at::timestamp as device_exposure_end_datetime,
    32817 as device_type_concept_id,   -- EHR
    null::varchar(255) as unique_device_id,
    null::varchar(255) as production_id,
    null::int as quantity,
    null::int as provider_id,
    visit_occurrence_id,
    null::int as visit_detail_id,
    code::varchar(50) as device_source_value,
    coalesce(source_concept_id, 0) as device_source_concept_id,
    null::int as unit_concept_id,
    null::varchar(50) as unit_source_value,
    null::int as unit_source_concept_id
from {{ ref('int_event') }}
where omop_table = 'device_exposure'
