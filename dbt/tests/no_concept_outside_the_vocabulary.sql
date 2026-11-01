-- Every non-zero concept in the main concept columns must exist, be standard, and sit in the right domain.
with used as (
    select condition_concept_id as concept_id, 'Condition' as domain_id from {{ ref('condition_occurrence') }}
    union select procedure_concept_id, 'Procedure' from {{ ref('procedure_occurrence') }}
    union select drug_concept_id, 'Drug' from {{ ref('drug_exposure') }}
    union select measurement_concept_id, 'Measurement' from {{ ref('measurement') }}
    union select visit_concept_id, 'Visit' from {{ ref('visit_occurrence') }}
    union select gender_concept_id, 'Gender' from {{ ref('person') }}
    union select race_concept_id, 'Race' from {{ ref('person') }}
    union select ethnicity_concept_id, 'Ethnicity' from {{ ref('person') }}
)

select u.concept_id, u.domain_id as expected_domain, c.domain_id, c.standard_concept
from used u
left join vocab.concept c using (concept_id)
where u.concept_id <> 0
  and (c.concept_id is null or c.standard_concept is distinct from 'S' or c.domain_id <> u.domain_id)
