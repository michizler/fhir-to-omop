-- Fails if a resource type has no recorded decision, or if a loaded type lost rows on the way to OMOP.
select * from {{ ref('int_resource_accounting') }}
where disposition is null or not accounted_for
