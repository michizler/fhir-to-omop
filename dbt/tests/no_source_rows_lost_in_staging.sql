-- Every raw resource of a staged type must reach staging. An Observation may expand into several rows, so it is
-- compared on distinct IDs. Any row returned here fails the test.
with raw_counts as (
    select resource_type, count(*) as n from {{ source('raw', 'fhir_resource') }} group by 1
),

staged as (
    select 'Patient' as resource_type, count(*) as n from {{ ref('stg_patient') }}
    union all select 'Encounter', count(*) from {{ ref('stg_encounter') }}
    union all select 'Condition', count(*) from {{ ref('stg_condition') }}
    union all select 'Procedure', count(*) from {{ ref('stg_procedure') }}
    union all select 'Immunization', count(*) from {{ ref('stg_immunization') }}
    union all select 'MedicationRequest', count(*) from {{ ref('stg_medication_request') }}
    union all select 'AllergyIntolerance', count(*) from {{ ref('stg_allergy') }}
    union all select 'Observation', count(distinct observation_id) from {{ ref('stg_observation') }}
)

select s.resource_type, r.n as raw_rows, s.n as staged_rows
from staged s
left join raw_counts r using (resource_type)
where s.n <> coalesce(r.n, -1)
