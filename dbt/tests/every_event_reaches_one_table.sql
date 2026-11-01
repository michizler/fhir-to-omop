-- The rows across the event tables must equal the rows in the event model, so routing neither lost nor doubled any.
with routed as (
    select count(*) as n from {{ ref('condition_occurrence') }}
    union all select count(*) from {{ ref('procedure_occurrence') }}
    union all select count(*) from {{ ref('drug_exposure') }}
    union all select count(*) from {{ ref('measurement') }}
    union all select count(*) from {{ ref('observation') }}
    union all select count(*) from {{ ref('device_exposure') }}
)

select (select sum(n) from routed) as routed_rows, (select count(*) from {{ ref('int_event') }}) as event_rows
where (select sum(n) from routed) <> (select count(*) from {{ ref('int_event') }})
