-- Where every FHIR record went. Each resource type is loaded, used to read another record, or left out with a reason.
-- A new resource type with no decision shows here with a NULL disposition, which fails a test.
with raw_counts as (
    select resource_type, count(*) as raw_rows from {{ source('raw', 'fhir_resource') }} group by 1
),

reached as (
    select 'Patient' as resource_type, count(*) as rows_in_omop from {{ ref('person') }}
    union all select 'Encounter', count(*) from {{ ref('visit_occurrence') }}
    union all
    select source_table, count(distinct source_id) from {{ ref('int_event') }} group by 1
)

select
    r.resource_type,
    r.raw_rows,
    d.disposition,
    d.destination,
    d.reason,
    x.rows_in_omop,
    case when d.disposition = 'loaded' then r.raw_rows = coalesce(x.rows_in_omop, 0) else true end as accounted_for
from raw_counts r
left join {{ ref('resource_disposition') }} d using (resource_type)
left join reached x using (resource_type)
