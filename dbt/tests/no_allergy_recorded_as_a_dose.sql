-- An allergy must never become a drug exposure, because that would say the patient took what they are allergic to.
select event_id, code, code_display, omop_table
from {{ ref('int_event') }}
where source_table = 'AllergyIntolerance' and omop_table <> 'observation'
