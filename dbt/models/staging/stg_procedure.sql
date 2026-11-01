-- One row per procedure.
select
    resource_id as procedure_id,
    patient_id,
    {{ ref_id('encounter,reference') }} as encounter_id,
    resource #>> '{code,coding,0,system}' as code_system,
    resource #>> '{code,coding,0,code}' as code,
    resource #>> '{code,coding,0,display}' as code_display,
    {{ ts('performedPeriod,start') }} as started_at,
    {{ ts('performedPeriod,end') }} as ended_at
from {{ source('raw', 'fhir_resource') }}
where resource_type = 'Procedure'
