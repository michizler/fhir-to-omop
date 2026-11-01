-- One row per patient. Race and ethnicity sit in US Core extensions, so they are read by URL rather than position.
select
    resource_id as patient_id,
    resource ->> 'gender' as gender,
    (resource ->> 'birthDate')::date as birth_date,
    (resource ->> 'deceasedDateTime')::timestamptz as deceased_at,
    resource #>> '{address,0,city}' as city,
    resource #>> '{address,0,state}' as state,
    resource #>> '{address,0,postalCode}' as postal_code,
    (resource #>> '{address,0,extension,0,extension,0,valueDecimal}')::numeric as latitude,
    (resource #>> '{address,0,extension,0,extension,1,valueDecimal}')::numeric as longitude,
    (select e -> 'extension' -> 0 -> 'valueCoding' ->> 'code'
     from jsonb_array_elements(resource -> 'extension') e
     where e ->> 'url' like '%us-core-race') as race_code,
    (select e -> 'extension' -> 0 -> 'valueCoding' ->> 'code'
     from jsonb_array_elements(resource -> 'extension') e
     where e ->> 'url' like '%us-core-ethnicity') as ethnicity_code
from {{ source('raw', 'fhir_resource') }}
where resource_type = 'Patient'
