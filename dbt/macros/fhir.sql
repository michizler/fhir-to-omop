{# Small helpers for reading FHIR. A reference such as "urn:uuid:abc" points at the resource with id "abc". #}
{% macro ref_id(path) -%}
    replace(resource #>> '{ {{- path -}} }', 'urn:uuid:', '')
{%- endmacro %}

{% macro ts(path) -%}
    (resource #>> '{ {{- path -}} }')::timestamptz
{%- endmacro %}
