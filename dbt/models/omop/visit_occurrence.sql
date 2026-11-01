-- OMOP visit_occurrence. The FHIR encounter class decides the visit concept.
select
    v.visit_occurrence_id,
    p.person_id,
    m.visit_concept_id,
    e.started_at::date as visit_start_date,
    e.started_at::timestamp as visit_start_datetime,
    coalesce(e.ended_at, e.started_at)::date as visit_end_date,
    coalesce(e.ended_at, e.started_at)::timestamp as visit_end_datetime,
    32827 as visit_type_concept_id,   -- EHR encounter record
    null::int as provider_id,
    null::int as care_site_id,
    e.class_code::varchar(50) as visit_source_value,
    0 as visit_source_concept_id,
    null::int as admitted_from_concept_id,
    null::varchar(50) as admitted_from_source_value,
    null::int as discharged_to_concept_id,
    null::varchar(50) as discharged_to_source_value,
    null::int as preceding_visit_occurrence_id
from {{ ref('stg_encounter') }} e
join {{ ref('int_visit') }} v using (encounter_id)
join {{ ref('int_person') }} p using (patient_id)
join {{ ref('visit_class_map') }} m using (class_code)
