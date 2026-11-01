"""The vocabulary reader must keep odd characters, treat empty fields as NULL and filter only what it says it filters."""
import io

from fhir_to_omop.vocabulary import concepts_kept, maps_to, read_rows

CONCEPT = (
    "concept_id\tconcept_name\tvocabulary_id\tstandard_concept\n"
    '1\tKnown "quoted" name\tSNOMED\tS\n'
    "2\tBrand pack\tNDC\t\n"
)
RELATION = (
    "concept_id_1\tconcept_id_2\trelationship_id\n"
    "1\t10\tMaps to\n"
    "1\t11\tIs a\n"
    "2\t12\tMaps to\n"
)


def rows(text):
    return list(read_rows(io.StringIO(text)))


def test_quote_marks_are_kept_as_characters():
    assert rows(CONCEPT)[0]["concept_name"] == 'Known "quoted" name'


def test_empty_field_becomes_null():
    assert rows(CONCEPT)[1]["standard_concept"] is None


def test_only_kept_vocabularies_load():
    assert [r["concept_id"] for r in concepts_kept(rows(CONCEPT))] == ["1"]


def test_only_maps_to_from_kept_concepts_load():
    assert [(r["concept_id_1"], r["concept_id_2"]) for r in maps_to(rows(RELATION), {1})] == [("1", "10")]
