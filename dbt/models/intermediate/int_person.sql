-- OMOP needs integer IDs. Numbering in ID order gives the same numbers on every rebuild of the same data.
select patient_id, row_number() over (order by patient_id)::int as person_id
from {{ ref('stg_patient') }}
