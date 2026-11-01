{# Uniqueness across several columns, without adding a package for one test. Returns the repeated keys. #}
{% test dbt_utils_free_unique(model, columns) %}
    select {{ columns }}, count(*) as n
    from {{ model }}
    group by {{ columns }}
    having count(*) > 1
{% endtest %}
