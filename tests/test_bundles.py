"""The parser keeps every entry, in order and unchanged, and refuses input that would misattribute records."""
import json
from pathlib import Path

import pytest

from fhir_to_omop.bundles import parse_bundle

MINI = (Path(__file__).parent / "fixtures" / "mini_bundle.json").read_bytes()


def test_every_entry_is_kept_in_order():
    b = parse_bundle(MINI, "mini.json")
    assert [(e.index, e.resource_type, e.resource_id) for e in b.entries] == [
        (0, "Patient", "p-1"), (1, "Encounter", "e-1"), (2, "Condition", "c-1")]


def test_every_entry_inherits_the_bundle_patient():
    assert {e.patient_id for e in parse_bundle(MINI, "mini.json").entries} == {"p-1"}


def test_resource_is_unchanged():
    original = json.loads(MINI)["entry"][2]["resource"]
    assert json.loads(parse_bundle(MINI, "mini.json").entries[2].resource_json) == original


def test_shared_file_has_no_patient():
    raw = json.dumps({"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Organization", "id": "o-1"}}]})
    assert parse_bundle(raw.encode(), "hospital.json").entries[0].patient_id is None


def test_two_patients_in_one_bundle_stops_the_load():
    doc = json.loads(MINI)
    doc["entry"].append({"resource": {"resourceType": "Patient", "id": "p-2"}})
    with pytest.raises(ValueError, match="2 Patient"):
        parse_bundle(json.dumps(doc).encode(), "bad.json")


def test_non_bundle_is_refused():
    with pytest.raises(ValueError, match="not a FHIR Bundle"):
        parse_bundle(b'{"resourceType": "Patient", "id": "p-1"}', "bad.json")


def test_hash_changes_with_content():
    assert parse_bundle(MINI, "a").sha256 != parse_bundle(MINI + b" ", "a").sha256
