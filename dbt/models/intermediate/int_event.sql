-- All clinical facts in one shape, each with its standard concept and the OMOP table it belongs in.
-- OMOP routes a row by what its concept is, not by what FHIR called it. "Medication review due" arrives as a Condition
-- but its concept is an observation, so it goes to the observation table. A code with no standard concept stays in the
-- table its FHIR type suggests, with concept 0 and the source code kept, so the fact is not lost.
--
-- Allergies are the one exception to routing by concept. An allergy's code names the substance, so routing it would
-- record a penicillin allergy as a dose of penicillin. Every allergy becomes "Allergic disposition" in the observation
-- table, with the substance as its value.
with facts as (
    select 'Condition' as source_table, condition_id as source_id, 0 as component_index, patient_id, encounter_id,
           onset_at as started_at, abated_at as ended_at, code_system, code, code_display,
           null::numeric as value_number, null::text as value_unit, null::text as value_code_system,
           null::text as value_code, null::text as value_text, 'Condition' as default_domain
    from {{ ref('stg_condition') }}
    union all
    select 'Procedure', procedure_id, 0, patient_id, encounter_id, started_at, ended_at, code_system, code, code_display,
           null, null, null, null, null, 'Procedure'
    from {{ ref('stg_procedure') }}
    union all
    select 'MedicationRequest', medication_request_id, 0, patient_id, encounter_id, authored_at, null, code_system, code,
           code_display, null, null, null, null, null, 'Drug'
    from {{ ref('stg_medication_request') }}
    union all
    select 'Immunization', immunization_id, 0, patient_id, encounter_id, given_at, null, code_system, code, code_display,
           null, null, null, null, null, 'Drug'
    from {{ ref('stg_immunization') }}
    union all
    select 'AllergyIntolerance', allergy_id, 0, patient_id, null, recorded_at, null, code_system, code, code_display,
           null, null, null, null, null, 'Observation'
    from {{ ref('stg_allergy') }}
    union all
    select 'Observation', observation_id, component_index, patient_id, encounter_id, observed_at, null, code_system, code,
           code_display, value_number, value_unit, value_code_system, value_code, value_text, 'Observation'
    from {{ ref('stg_observation') }}
),

good_map as (
    select code_system, code, source_concept_id, target_concept_id, target_domain
    from {{ ref('int_code_map') }}
    where map_status in ('mapped', 'already_standard')
),

source_concept as (
    select distinct code_system, code, source_concept_id from {{ ref('int_code_map') }}
),

-- An answer or unit needs one concept. The rare code with two targets takes the lowest ID, so the choice is repeatable.
single_concept as (
    select code_system, code, min(target_concept_id) as concept_id from good_map group by 1, 2
),

joined as (
    select
        f.*,
        s.source_concept_id,
        case when f.source_table = 'AllergyIntolerance' then 43530807   -- Allergic disposition
             else coalesce(m.target_concept_id, 0) end as concept_id,
        coalesce(m.target_domain, f.default_domain) as domain_id,
        coalesce(v.concept_id, a.concept_id) as value_concept_id,
        u.concept_id as unit_concept_id
    from facts f
    left join good_map m
        on m.code_system = f.code_system and m.code = f.code and f.source_table <> 'AllergyIntolerance'
    left join source_concept s on s.code_system = f.code_system and s.code = f.code
    left join single_concept v on v.code_system = f.value_code_system and v.code = f.value_code
    left join single_concept a
        on a.code_system = f.code_system and a.code = f.code and f.source_table = 'AllergyIntolerance'
    left join single_concept u on u.code_system = 'http://unitsofmeasure.org' and u.code = f.value_unit
)

select
    row_number() over (order by source_table, source_id, component_index, concept_id)::int as event_id,
    j.*,
    case domain_id
        when 'Condition' then 'condition_occurrence'
        when 'Procedure' then 'procedure_occurrence'
        when 'Drug' then 'drug_exposure'
        when 'Measurement' then 'measurement'
        when 'Device' then 'device_exposure'
        else 'observation'
    end as omop_table,
    p.person_id,
    vis.visit_occurrence_id
from joined j
join {{ ref('int_person') }} p on p.patient_id = j.patient_id
left join {{ ref('int_visit') }} vis on vis.encounter_id = j.encounter_id
