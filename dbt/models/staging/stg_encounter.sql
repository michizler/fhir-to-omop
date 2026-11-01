-- One row per encounter. The class says what kind of visit it was, which later decides the OMOP visit concept.
select
    resource_id as encounter_id,
    patient_id,
    resource #>> '{class,code}' as class_code,
    resource #>> '{type,0,coding,0,code}' as type_code,
    resource #>> '{type,0,coding,0,display}' as type_display,
    {{ ts('period,start') }} as started_at,
    {{ ts('period,end') }} as ended_at,
    resource #>> '{reasonCode,0,coding,0,code}' as reason_code
from {{ source('raw', 'fhir_resource') }}
where resource_type = 'Encounter'
