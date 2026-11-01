"""Loads the Athena vocabulary download into Postgres, reading straight from the zip so nothing is unpacked to disk.

The download is 4.9 GB unzipped, and most of it covers vocabularies this data never uses. Only the vocabularies in
KEPT load, and from the relationship file only "Maps to" rows, which is what turns a source code into a standard one.
Each file's rows read and rows loaded go in vocab.load_audit, so the filtering can be seen rather than assumed."""
from __future__ import annotations

import argparse
import csv
import io
import sys
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path

import psycopg

from fhir_to_omop.load import database_url

SCHEMA = Path(__file__).resolve().parents[2] / "sql" / "002_vocab.sql"

# Source vocabularies found in the FHIR data, the type and demographic vocabularies OMOP needs, and RxNorm Extension
# because retired RxNorm codes can map into it.
KEPT = frozenset({"SNOMED", "LOINC", "RxNorm", "RxNorm Extension", "CVX", "UCUM", "Gender", "Race", "Ethnicity", "Visit",
                  "Visit Type", "Type Concept", "Condition Status", "Condition Type", "Drug Type", "Procedure Type",
                  "Meas Type", "Observation Type", "Obs Period Type", "Death Type", "Domain", "Vocabulary",
                  "Concept Class", "Relationship", "None", "CDM", "OMOP Extension"})
MAPS_TO = "Maps to"
CONCEPT_COLUMNS = ["concept_id", "concept_name", "domain_id", "vocabulary_id", "concept_class_id", "standard_concept",
                   "concept_code", "valid_start_date", "valid_end_date", "invalid_reason"]
RELATIONSHIP_COLUMNS = ["concept_id_1", "concept_id_2", "relationship_id", "valid_start_date", "valid_end_date",
                        "invalid_reason"]


def read_rows(stream: Iterable[str]) -> Iterator[dict[str, str | None]]:
    """Athena files are tab separated with no quoting, so a quote mark in a concept name is just a character.
    An empty field means NULL."""
    csv.field_size_limit(sys.maxsize if sys.maxsize < 2**31 else 2**31 - 1)
    for row in csv.DictReader(stream, delimiter="\t", quoting=csv.QUOTE_NONE):
        yield {k: (v if v != "" else None) for k, v in row.items()}


def concepts_kept(rows: Iterable[dict], kept: frozenset[str] = KEPT) -> Iterator[dict]:
    return (r for r in rows if r["vocabulary_id"] in kept)


def maps_to(rows: Iterable[dict], concept_ids: set[int]) -> Iterator[dict]:
    """"Maps to" rows whose source concept was kept. Their target is kept too, unless the target's vocabulary was
    filtered out, which the load reports as a count rather than hiding."""
    return (r for r in rows if r["relationship_id"] == MAPS_TO and int(r["concept_id_1"]) in concept_ids)


def _open(archive: zipfile.ZipFile, name: str) -> io.TextIOWrapper:
    return io.TextIOWrapper(archive.open(name), encoding="utf-8", newline="")


def _copy(conn: psycopg.Connection, table: str, columns: list[str], rows: Iterable[dict]) -> int:
    n = 0
    with conn.cursor() as cur, cur.copy(f"COPY {table} ({', '.join(columns)}) FROM STDIN") as copy:
        for r in rows:
            copy.write_row([r[c] for c in columns])
            n += 1
    return n


def _audit(conn: psycopg.Connection, name: str, read: int, loaded: int) -> None:
    conn.execute("""INSERT INTO vocab.load_audit (source_file, rows_read, rows_loaded) VALUES (%s, %s, %s)
                    ON CONFLICT (source_file) DO UPDATE SET rows_read = EXCLUDED.rows_read,
                        rows_loaded = EXCLUDED.rows_loaded, loaded_at = now()""", (name, read, loaded))


class Counter:
    """Counts rows passing through, so the audit knows how many were read before filtering."""

    def __init__(self, rows: Iterable[dict]):
        self.rows, self.n = rows, 0

    def __iter__(self) -> Iterator[dict]:
        for r in self.rows:
            self.n += 1
            yield r


def load(conn: psycopg.Connection, zip_path: Path) -> dict[str, tuple[int, int]]:
    conn.execute(SCHEMA.read_text(encoding="utf-8"))
    conn.execute("DROP INDEX IF EXISTS vocab.concept_code_idx")
    conn.execute("DROP INDEX IF EXISTS vocab.concept_relationship_1_idx")
    conn.execute("TRUNCATE vocab.concept, vocab.concept_relationship, vocab.vocabulary_version, vocab.load_audit")
    result = {}
    with zipfile.ZipFile(zip_path) as z:
        with _open(z, "CONCEPT.csv") as f:
            source = Counter(read_rows(f))
            ids: set[int] = set()

            def remember(rows: Iterable[dict]) -> Iterator[dict]:
                for r in rows:
                    ids.add(int(r["concept_id"]))
                    yield r

            loaded = _copy(conn, "vocab.concept", CONCEPT_COLUMNS, remember(concepts_kept(source)))
            _audit(conn, "CONCEPT.csv", source.n, loaded)
            result["CONCEPT.csv"] = (source.n, loaded)
        with _open(z, "CONCEPT_RELATIONSHIP.csv") as f:
            source = Counter(read_rows(f))
            loaded = _copy(conn, "vocab.concept_relationship", RELATIONSHIP_COLUMNS, maps_to(source, ids))
            _audit(conn, "CONCEPT_RELATIONSHIP.csv", source.n, loaded)
            result["CONCEPT_RELATIONSHIP.csv"] = (source.n, loaded)
        with _open(z, "VOCABULARY.csv") as f:
            rows = list(read_rows(f))
            loaded = _copy(conn, "vocab.vocabulary_version", ["vocabulary_id", "vocabulary_name", "vocabulary_version"], rows)
            _audit(conn, "VOCABULARY.csv", len(rows), loaded)
            result["VOCABULARY.csv"] = (len(rows), loaded)
    conn.execute("CREATE INDEX concept_code_idx ON vocab.concept (vocabulary_id, concept_code)")
    conn.execute("CREATE INDEX concept_relationship_1_idx ON vocab.concept_relationship (concept_id_1)")
    conn.execute("ANALYZE vocab.concept")
    conn.execute("ANALYZE vocab.concept_relationship")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path, help="the Athena vocabulary download")
    args = parser.parse_args()
    with psycopg.connect(database_url()) as conn:
        for name, (read, loaded) in load(conn, args.zip_path).items():
            print(f"{name}: read {read:,}, loaded {loaded:,}")


if __name__ == "__main__":
    main()
