"""Loads a folder of FHIR bundles into raw.fhir_resource. Each file is replaced in one transaction, so a rerun gives
the same table, and the file only counts as loaded when the row count in Postgres matches the count in the file."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg

from fhir_to_omop.bundles import Bundle, bundle_paths, parse_bundle

SCHEMA = Path(__file__).resolve().parents[2] / "sql" / "001_raw.sql"
COLUMNS = "(source_file, entry_index, resource_type, resource_id, patient_id, resource)"


def ensure_schema(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA.read_text(encoding="utf-8"))
    conn.commit()


def load_bundle(conn: psycopg.Connection, bundle: Bundle) -> int:
    """Replaces one file's rows and records it in the audit table. Raises, and rolls back, on a count mismatch."""
    with conn.transaction():
        conn.execute("DELETE FROM raw.fhir_resource WHERE source_file = %s", (bundle.source_file,))
        with conn.cursor() as cur, cur.copy(f"COPY raw.fhir_resource {COLUMNS} FROM STDIN") as copy:
            for e in bundle.entries:
                copy.write_row((bundle.source_file, e.index, e.resource_type, e.resource_id, e.patient_id, e.resource_json))
        loaded = conn.execute("SELECT count(*) FROM raw.fhir_resource WHERE source_file = %s",
                              (bundle.source_file,)).fetchone()[0]
        if loaded != len(bundle.entries):
            raise RuntimeError(f"{bundle.source_file}: {len(bundle.entries)} entries in file, {loaded} loaded")
        conn.execute(
            """INSERT INTO raw.load_audit (source_file, sha256, entries_in_file, entries_loaded)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (source_file) DO UPDATE SET sha256 = EXCLUDED.sha256, loaded_at = now(),
                   entries_in_file = EXCLUDED.entries_in_file, entries_loaded = EXCLUDED.entries_loaded""",
            (bundle.source_file, bundle.sha256, len(bundle.entries), loaded))
    return loaded


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://omop:local-dev-only@127.0.0.1:5433/omop")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="folder of FHIR bundle JSON files")
    args = parser.parse_args()
    paths = bundle_paths(args.folder)
    if not paths:
        raise SystemExit(f"no bundles in {args.folder}")
    with psycopg.connect(database_url()) as conn:
        ensure_schema(conn)
        total = sum(load_bundle(conn, parse_bundle(p.read_bytes(), p.name)) for p in paths)
    print(f"loaded {total} entries from {len(paths)} files")


if __name__ == "__main__":
    main()
