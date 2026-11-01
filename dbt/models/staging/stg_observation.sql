-- One row per measured value. A blood pressure arrives as one Observation holding two components, so components
-- become rows of their own, and an Observation with components gets no row of its own because it holds no value.
with obs as (
    select resource_id, patient_id, resource
    from {{ source('raw', 'fhir_resource') }}
    where resource_type = 'Observation'
),

single_values as (
    select resource_id as observation_id, 0 as component_index, patient_id, resource, resource as part
    from obs
    where not resource ? 'component'
),

component_values as (
    select o.resource_id, c.ordinality::int, o.patient_id, o.resource, c.value
    from obs o
    cross join lateral jsonb_array_elements(o.resource -> 'component') with ordinality c
    where o.resource ? 'component'
),

all_values as (
    select * from single_values
    union all
    select * from component_values
)

select
    observation_id,
    component_index,
    patient_id,
    replace(resource #>> '{encounter,reference}', 'urn:uuid:', '') as encounter_id,
    resource #>> '{category,0,coding,0,code}' as category,
    part #>> '{code,coding,0,system}' as code_system,
    part #>> '{code,coding,0,code}' as code,
    part #>> '{code,coding,0,display}' as code_display,
    (resource ->> 'effectiveDateTime')::timestamptz as observed_at,
    (part #>> '{valueQuantity,value}')::numeric as value_number,
    part #>> '{valueQuantity,code}' as value_unit,
    part #>> '{valueCodeableConcept,coding,0,system}' as value_code_system,
    part #>> '{valueCodeableConcept,coding,0,code}' as value_code,
    part ->> 'valueString' as value_text
from all_values
