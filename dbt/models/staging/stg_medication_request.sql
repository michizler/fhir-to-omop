-- One row per prescription. About three in ten name their drug through a separate Medication resource rather than
-- inline, so reading only the inline code would silently lose them. Both shapes end up in the same columns.
with requests as (
    select * from {{ source('raw', 'fhir_resource') }} where resource_type = 'MedicationRequest'
),

medications as (
    select resource_id, resource -> 'code' as code
    from {{ source('raw', 'fhir_resource') }}
    where resource_type = 'Medication'
)

select
    r.resource_id as medication_request_id,
    r.patient_id,
    replace(r.resource #>> '{encounter,reference}', 'urn:uuid:', '') as encounter_id,
    case when r.resource ? 'medicationReference' then 'reference' else 'inline' end as drug_source,
    coalesce(r.resource #>> '{medicationCodeableConcept,coding,0,system}', m.code #>> '{coding,0,system}') as code_system,
    coalesce(r.resource #>> '{medicationCodeableConcept,coding,0,code}', m.code #>> '{coding,0,code}') as code,
    coalesce(r.resource #>> '{medicationCodeableConcept,coding,0,display}', m.code #>> '{coding,0,display}') as code_display,
    (r.resource ->> 'authoredOn')::timestamptz as authored_at,
    r.resource ->> 'status' as status
from requests r
left join medications m
    on m.resource_id = replace(r.resource #>> '{medicationReference,reference}', 'urn:uuid:', '')
