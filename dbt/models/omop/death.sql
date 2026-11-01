-- OMOP death: one row for each patient with a death date. The cause comes from the death certificate record, LOINC
-- 69453-9, which arrives at a paperwork visit after the death. Not every death has one, so the cause can be empty.
with certificates as (
    select person_id, min(value_concept_id) as cause_concept_id, min(value_code) as cause_code
    from {{ ref('int_event') }}
    where code = '69453-9'
    group by person_id
)

select
    x.person_id,
    p.deceased_at::date as death_date,
    p.deceased_at::timestamp as death_datetime,
    32817 as death_type_concept_id,   -- EHR
    c.cause_concept_id,
    c.cause_code::varchar(50) as cause_source_value,
    null::int as cause_source_concept_id
from {{ ref('stg_patient') }} p
join {{ ref('int_person') }} x using (patient_id)
left join certificates c using (person_id)
where p.deceased_at is not null
