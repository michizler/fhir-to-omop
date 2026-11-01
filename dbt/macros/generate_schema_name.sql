{# Uses the schema named on the model as it is, so staging models land in "staging" and not "public_staging". #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name if custom_schema_name else target.schema }}
{%- endmacro %}
