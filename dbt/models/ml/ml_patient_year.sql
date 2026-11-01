-- One row per person per year, for predicting an emergency visit in the coming year. Features use OMOP tables only and
-- only events before 1 January of that year, so a model can't see the future and the same query would run on any OMOP
-- site. A person counts for a year if they were alive on 1 January and had at least a year of earlier records.
{% set condition_features = {
    'hypertension': [320128], 'prediabetes': [37018196], 'diabetes': [201826], 'anemia': [439777],
    'chronic_pain': [436096], 'low_back_pain': [4132891], 'ischemic_heart': [4185932], 'metabolic_syndrome': [436940],
    'obesity': [4060985], 'severe_anxiety': [4214746], 'social_isolation': [4309238], 'limited_social': [4172829],
    'risk_activity': [4059650], 'asthma': [317009, 4051466], 'kidney_disease': [192279, 443614, 443601, 443597, 443612],
    'seizures': [4029498, 380378], 'overdose': [607147], 'opioid_use': [438130], 'heart_failure': [4229440],
    'alzheimers': [378419, 4043241], 'emphysema': [261325, 258780], 'injury': [443419, 75053, 4001336, 375671]
} %}

with cohort as (
    select p.person_id, y.index_year, make_date(y.index_year, 1, 1) as index_date, p.year_of_birth, p.gender_concept_id
    from {{ ref('person') }} p
    cross join generate_series(2018, 2025) as y(index_year)
    join {{ ref('observation_period') }} o using (person_id)
    left join {{ ref('death') }} d using (person_id)
    where o.observation_period_start_date <= make_date(y.index_year - 1, 1, 1)
      and o.observation_period_end_date >= make_date(y.index_year, 1, 1)
      and (d.death_date is null or d.death_date >= make_date(y.index_year, 1, 1))
),

visits as (
    select
        c.person_id, c.index_year,
        count(*) filter (where v.visit_concept_id = 9203 and v.visit_start_date >= c.index_date - interval '1 year') as er_visits_1y,
        count(*) filter (where v.visit_concept_id = 9203) as er_visits_3y,
        count(*) filter (where v.visit_concept_id = 9201 and v.visit_start_date >= c.index_date - interval '1 year') as inpatient_visits_1y,
        count(*) filter (where v.visit_concept_id = 9201) as inpatient_visits_3y,
        count(*) filter (where v.visit_concept_id = 9202 and v.visit_start_date >= c.index_date - interval '1 year') as outpatient_visits_1y
    from cohort c
    join {{ ref('visit_occurrence') }} v
        on v.person_id = c.person_id
       and v.visit_start_date < c.index_date
       and v.visit_start_date >= c.index_date - interval '3 years'
    group by 1, 2
),

drugs as (
    select c.person_id, c.index_year, count(distinct d.drug_concept_id) as distinct_drugs_1y
    from cohort c
    join {{ ref('drug_exposure') }} d
        on d.person_id = c.person_id
       and d.drug_exposure_start_date < c.index_date
       and d.drug_exposure_start_date >= c.index_date - interval '1 year'
    group by 1, 2
),

conditions as (
    select
        c.person_id, c.index_year
        {%- for name, ids in condition_features.items() %},
        bool_or(x.condition_concept_id in ({{ ids | join(', ') }}))::int as {{ name }}
        {%- endfor %}
    from cohort c
    join {{ ref('condition_occurrence') }} x
        on x.person_id = c.person_id and x.condition_start_date < c.index_date
    group by 1, 2
),

latest as (
    select person_id, index_year, measurement_concept_id, value_as_number,
           row_number() over (partition by person_id, index_year, measurement_concept_id
                              order by measurement_date desc, measurement_id desc) as r
    from cohort c
    join {{ ref('measurement') }} m using (person_id)
    where m.measurement_concept_id in (3004249, 3038553)   -- systolic blood pressure, body mass index
      and m.measurement_date < c.index_date
      and m.measurement_date >= c.index_date - interval '3 years'
      and m.value_as_number is not null
),

outcome as (
    select distinct c.person_id, c.index_year
    from cohort c
    join {{ ref('visit_occurrence') }} v
        on v.person_id = c.person_id
       and v.visit_concept_id = 9203
       and v.visit_start_date >= c.index_date
       and v.visit_start_date < c.index_date + interval '1 year'
)

select
    c.person_id,
    c.index_year,
    (o.person_id is not null)::int as emergency_next_year,
    c.index_year - c.year_of_birth as age,
    (c.gender_concept_id = 8532)::int as female,
    coalesce(v.er_visits_1y, 0) as er_visits_1y,
    coalesce(v.er_visits_3y, 0) as er_visits_3y,
    coalesce(v.inpatient_visits_1y, 0) as inpatient_visits_1y,
    coalesce(v.inpatient_visits_3y, 0) as inpatient_visits_3y,
    coalesce(v.outpatient_visits_1y, 0) as outpatient_visits_1y,
    coalesce(d.distinct_drugs_1y, 0) as distinct_drugs_1y,
    sbp.value_as_number as systolic_bp,
    bmi.value_as_number as bmi
    {%- for name in condition_features %},
    coalesce(x.{{ name }}, 0) as {{ name }}
    {%- endfor %}
from cohort c
left join visits v using (person_id, index_year)
left join drugs d using (person_id, index_year)
left join conditions x using (person_id, index_year)
left join outcome o using (person_id, index_year)
left join latest sbp on sbp.person_id = c.person_id and sbp.index_year = c.index_year
    and sbp.measurement_concept_id = 3004249 and sbp.r = 1
left join latest bmi on bmi.person_id = c.person_id and bmi.index_year = c.index_year
    and bmi.measurement_concept_id = 3038553 and bmi.r = 1
