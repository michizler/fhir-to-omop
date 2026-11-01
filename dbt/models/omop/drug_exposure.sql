-- OMOP drug_exposure: prescriptions and vaccines. FHIR gives no end date for either, and OMOP requires one, so the end
-- is the start date. That means this table says a drug was prescribed, not how long it was taken.
select
    event_id as drug_exposure_id,
    person_id,
    concept_id as drug_concept_id,
    started_at::date as drug_exposure_start_date,
    started_at::timestamp as drug_exposure_start_datetime,
    started_at::date as drug_exposure_end_date,
    started_at::timestamp as drug_exposure_end_datetime,
    null::date as verbatim_end_date,
    32817 as drug_type_concept_id,   -- EHR
    null::varchar(20) as stop_reason,
    null::int as refills,
    null::numeric as quantity,
    null::int as days_supply,
    null::text as sig,
    null::int as route_concept_id,
    null::varchar(50) as lot_number,
    null::int as provider_id,
    visit_occurrence_id,
    null::int as visit_detail_id,
    code::varchar(50) as drug_source_value,
    coalesce(source_concept_id, 0) as drug_source_concept_id,
    null::varchar(50) as route_source_value,
    null::varchar(50) as dose_unit_source_value
from {{ ref('int_event') }}
where omop_table = 'drug_exposure'
