-- One row per condition. An empty end date means it is still active.
select
    resource_id as condition_id,
    patient_id,
    {{ ref_id('encounter,reference') }} as encounter_id,
    resource #>> '{code,coding,0,system}' as code_system,
    resource #>> '{code,coding,0,code}' as code,
    resource #>> '{code,coding,0,display}' as code_display,
    {{ ts('onsetDateTime') }} as onset_at,
    {{ ts('abatementDateTime') }} as abated_at,
    resource #>> '{clinicalStatus,coding,0,code}' as clinical_status
from {{ source('raw', 'fhir_resource') }}
where resource_type = 'Condition'
