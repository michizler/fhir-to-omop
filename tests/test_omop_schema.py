"""Proves each built table matches the official OMOP CDM 5.4 definition: same columns, same order, no required gaps."""
import re
from pathlib import Path

import psycopg
import pytest

from fhir_to_omop.load import database_url

DDL = (Path(__file__).parents[1] / "sql" / "reference" / "omop_cdm_5.4_ddl.sql").read_text(encoding="utf-8")
BUILT = ["person", "observation_period", "visit_occurrence", "condition_occurrence", "drug_exposure",
         "procedure_occurrence", "measurement", "observation", "device_exposure", "death"]


def official(table: str) -> list[tuple[str, bool]]:
    body = re.search(rf"CREATE TABLE @cdmDatabaseSchema\.{table} \((.*?)\);", DDL, re.DOTALL).group(1)
    lines = [ln.strip().rstrip(",") for ln in body.splitlines() if ln.strip()]
    return [(ln.split()[0], "NOT NULL" in ln) for ln in lines]


@pytest.fixture(scope="module")
def conn():
    try:
        c = psycopg.connect(database_url())
    except psycopg.OperationalError:
        pytest.skip("local Postgres is not running")
    yield c
    c.close()


def built_columns(conn, table):
    rows = conn.execute("""SELECT column_name FROM information_schema.columns
                           WHERE table_schema = 'omop' AND table_name = %s ORDER BY ordinal_position""", (table,)).fetchall()
    return [r[0] for r in rows]


@pytest.mark.parametrize("table", BUILT)
def test_columns_match_the_standard(conn, table):
    assert built_columns(conn, table) == [name for name, _ in official(table)]


@pytest.mark.parametrize("table", BUILT)
def test_required_columns_have_no_nulls(conn, table):
    for name, required in official(table):
        if required:
            nulls = conn.execute(f"SELECT count(*) FROM omop.{table} WHERE {name} IS NULL").fetchone()[0]
            assert nulls == 0, f"{table}.{name} has {nulls} nulls"
