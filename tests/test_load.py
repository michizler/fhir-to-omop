"""Against the local Postgres: a rerun changes nothing, and a changed file replaces only its own rows."""
import json
from pathlib import Path

import psycopg
import pytest

from fhir_to_omop.bundles import parse_bundle
from fhir_to_omop.load import database_url, ensure_schema, load_bundle

MINI = (Path(__file__).parent / "fixtures" / "mini_bundle.json").read_bytes()
TEST_FILES = ("test-a.json", "test-b.json")


@pytest.fixture
def conn():
    try:
        c = psycopg.connect(database_url())
    except psycopg.OperationalError:
        pytest.skip("local Postgres is not running")
    ensure_schema(c)
    yield c
    c.rollback()
    for table in ("raw.fhir_resource", "raw.load_audit"):
        c.execute(f"DELETE FROM {table} WHERE source_file = ANY(%s)", (list(TEST_FILES),))
    c.commit()
    c.close()


def count(conn, name):
    return conn.execute("SELECT count(*) FROM raw.fhir_resource WHERE source_file = %s", (name,)).fetchone()[0]


def test_load_matches_the_file(conn):
    assert load_bundle(conn, parse_bundle(MINI, TEST_FILES[0])) == 3
    assert conn.execute("SELECT entries_in_file, entries_loaded FROM raw.load_audit WHERE source_file = %s",
                        (TEST_FILES[0],)).fetchone() == (3, 3)


def test_rerun_gives_the_same_table(conn):
    load_bundle(conn, parse_bundle(MINI, TEST_FILES[0]))
    load_bundle(conn, parse_bundle(MINI, TEST_FILES[0]))
    assert count(conn, TEST_FILES[0]) == 3


def test_corrected_file_replaces_only_its_own_rows(conn):
    load_bundle(conn, parse_bundle(MINI, TEST_FILES[0]))
    load_bundle(conn, parse_bundle(MINI, TEST_FILES[1]))
    smaller = json.loads(MINI)
    smaller["entry"].pop()
    load_bundle(conn, parse_bundle(json.dumps(smaller).encode(), TEST_FILES[0]))
    assert (count(conn, TEST_FILES[0]), count(conn, TEST_FILES[1])) == (2, 3)


def test_resource_survives_jsonb_round_trip(conn):
    load_bundle(conn, parse_bundle(MINI, TEST_FILES[0]))
    stored = conn.execute("SELECT resource FROM raw.fhir_resource WHERE source_file = %s AND entry_index = 2",
                          (TEST_FILES[0],)).fetchone()[0]
    assert stored == json.loads(MINI)["entry"][2]["resource"]
