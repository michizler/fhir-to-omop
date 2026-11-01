-- Integer visit IDs, numbered in ID order so a rebuild of the same data gives the same numbers.
select encounter_id, row_number() over (order by encounter_id)::int as visit_occurrence_id
from {{ ref('stg_encounter') }}
