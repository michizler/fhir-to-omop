-- OMOP person. Race codes with no OMOP concept become 0, and the source code is kept.
select
    x.person_id,
    g.gender_concept_id,
    extract(year from p.birth_date)::int as year_of_birth,
    extract(month from p.birth_date)::int as month_of_birth,
    extract(day from p.birth_date)::int as day_of_birth,
    p.birth_date::timestamp as birth_datetime,
    coalesce(r.race_concept_id, 0) as race_concept_id,
    coalesce(e.ethnicity_concept_id, 0) as ethnicity_concept_id,
    null::int as location_id,
    null::int as provider_id,
    null::int as care_site_id,
    p.patient_id::varchar(50) as person_source_value,
    p.gender::varchar(50) as gender_source_value,
    0 as gender_source_concept_id,
    p.race_code::varchar(50) as race_source_value,
    0 as race_source_concept_id,
    p.ethnicity_code::varchar(50) as ethnicity_source_value,
    0 as ethnicity_source_concept_id
from {{ ref('stg_patient') }} p
join {{ ref('int_person') }} x using (patient_id)
join {{ ref('gender_map') }} g using (gender)
left join {{ ref('race_map') }} r using (race_code)
left join {{ ref('ethnicity_map') }} e using (ethnicity_code)
