-- Turns each source code into the standard OMOP concept it maps to, and records why when it can't.
-- One code can map to several standard concepts, so a code can have more than one row here.
with codes as (
    select distinct code_system, code from {{ ref('int_source_code') }}
),

source_concepts as (
    select c.code_system, c.code, s.vocabulary_id, sc.concept_id as source_concept_id, sc.invalid_reason as source_invalid_reason
    from codes c
    left join {{ ref('fhir_code_system') }} s on s.code_system = c.code_system
    left join vocab.concept sc on sc.vocabulary_id = s.vocabulary_id and sc.concept_code = c.code
),

targets as (
    select s.*, r.concept_id_2 as target_concept_id
    from source_concepts s
    left join vocab.concept_relationship r
        on r.concept_id_1 = s.source_concept_id and r.relationship_id = 'Maps to' and r.invalid_reason is null
)

select
    t.code_system,
    t.code,
    t.vocabulary_id,
    t.source_concept_id,
    t.source_invalid_reason,
    t.target_concept_id,
    tc.concept_name as target_concept_name,
    tc.domain_id as target_domain,
    tc.vocabulary_id as target_vocabulary,
    tc.standard_concept as target_standard,
    case
        when t.vocabulary_id is null then 'unknown_code_system'
        when t.source_concept_id is null then 'code_not_in_vocabulary'
        when t.target_concept_id is null then 'no_standard_map'
        when tc.concept_id is null then 'target_not_loaded'
        when tc.standard_concept is distinct from 'S' then 'target_not_standard'
        when t.target_concept_id = t.source_concept_id then 'already_standard'
        else 'mapped'
    end as map_status
from targets t
left join vocab.concept tc on tc.concept_id = t.target_concept_id
