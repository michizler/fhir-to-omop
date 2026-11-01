-- Every distinct clinical code in the data, with how many rows use it, so mapping can be measured by rows as well as
-- by distinct codes. A rare code that fails to map matters far less than a common one. Observation answers and units
-- are listed under their own names because they are not the main code on a row.
with used as (
    select 'Condition' as source_table, code_system, code, code_display from {{ ref('stg_condition') }}
    union all select 'Procedure', code_system, code, code_display from {{ ref('stg_procedure') }}
    union all select 'MedicationRequest', code_system, code, code_display from {{ ref('stg_medication_request') }}
    union all select 'Immunization', code_system, code, code_display from {{ ref('stg_immunization') }}
    union all select 'Observation', code_system, code, code_display from {{ ref('stg_observation') }}
    union all select 'AllergyIntolerance', code_system, code, code_display from {{ ref('stg_allergy') }}
    union all select 'ObservationValue', value_code_system, value_code, null from {{ ref('stg_observation') }} where value_code is not null
    union all select 'ObservationUnit', 'http://unitsofmeasure.org', value_unit, null from {{ ref('stg_observation') }} where value_unit is not null
)

select source_table, code_system, code, min(code_display) as code_display, count(*) as row_count
from used
group by source_table, code_system, code
