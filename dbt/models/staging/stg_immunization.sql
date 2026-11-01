-- One row per vaccine given.
select
    resource_id as immunization_id,
    patient_id,
    {{ ref_id('encounter,reference') }} as encounter_id,
    resource #>> '{vaccineCode,coding,0,system}' as code_system,
    resource #>> '{vaccineCode,coding,0,code}' as code,
    resource #>> '{vaccineCode,coding,0,display}' as code_display,
    {{ ts('occurrenceDateTime') }} as given_at
from {{ source('raw', 'fhir_resource') }}
where resource_type = 'Immunization'
