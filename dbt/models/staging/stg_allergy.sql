-- One row per recorded allergy. Allergies have no encounter in this data, so they attach to the patient only.
select
    resource_id as allergy_id,
    patient_id,
    resource #>> '{code,coding,0,system}' as code_system,
    resource #>> '{code,coding,0,code}' as code,
    resource #>> '{code,coding,0,display}' as code_display,
    {{ ts('recordedDate') }} as recorded_at
from {{ source('raw', 'fhir_resource') }}
where resource_type = 'AllergyIntolerance'
