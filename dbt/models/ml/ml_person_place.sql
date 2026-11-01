-- Where each person lives, used only to split people into simulated trusts. It is never a model feature.
select x.person_id, p.city, p.latitude, p.longitude
from {{ ref('stg_patient') }} p
join {{ ref('int_person') }} x using (patient_id)
