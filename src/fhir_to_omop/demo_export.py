"""Writes the small files the live demo needs, so the API needs neither Postgres nor the vocabularies: the mapping for
the codes in this data, plus example records. The output stays out of this repo, in data/demo."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import psycopg

from fhir_to_omop.load import database_url

OUT = Path(__file__).resolve().parents[2] / "data" / "demo"

CONCEPTS = """
select distinct on (m.code_system, m.code, m.target_concept_id) m.code_system, m.code, s.code_display, m.source_concept_id,
       m.target_concept_id, m.target_concept_name, m.target_domain, m.map_status
from intermediate.int_code_map m
join intermediate.int_source_code s using (code_system, code)
order by m.code_system, m.code, m.target_concept_id, s.code_display nulls last"""

ROUTING = """select source_table, omop_table, count(*) from intermediate.int_event group by 1, 2 order by 1, 3 desc"""

MAPPING = """
with s as (select source_table, code_system, code, row_count from intermediate.int_source_code
           where source_table not in ('ObservationValue', 'ObservationUnit')),
st as (select code_system, code, bool_or(map_status in ('mapped', 'already_standard')) ok
       from intermediate.int_code_map group by 1, 2)
select source_table, count(*), count(*) filter (where ok), sum(row_count), coalesce(sum(row_count) filter (where ok), 0)
from s join st using (code_system, code) group by 1 order by 4 desc"""

UNMAPPED = """
select s.source_table, s.code, s.code_display, m.map_status, s.row_count
from intermediate.int_source_code s join intermediate.int_code_map m using (code_system, code)
where m.map_status not in ('mapped', 'already_standard')
  and s.source_table not in ('ObservationValue', 'ObservationUnit')
order by s.row_count desc limit 12"""

# Each example shows one behaviour of the pipeline. The title says what to look for.
SAMPLES = [
    ("A diagnosis", "Prediabetes stays a condition.", "Condition", "resource #>> '{code,coding,0,code}' = '714628002'"),
    ("Not really a diagnosis", "FHIR calls this a Condition, but its concept is an observation.", "Condition",
     "resource #>> '{code,coding,0,code}' = '160903007'"),
    ("A drug allergy", "Routing by concept would record a dose of the drug, so it stays an observation.", "AllergyIntolerance",
     "resource #>> '{code,coding,0,display}' = 'Penicillin V'"),
    ("A vaccine logged as a procedure", "FHIR calls this a Procedure, but a drug was given.", "Procedure",
     "resource #>> '{code,coding,0,display}' like 'Administration of vaccine%%'"),
    ("A blood pressure reading", "One FHIR record holds two values, so it becomes two rows.", "Observation",
     "resource #>> '{code,coding,0,code}' = '85354-9'"),
    ("A prescription", "The RxNorm code is already a standard concept.", "MedicationRequest",
     "resource ? 'medicationCodeableConcept'"),
    ("A code with no standard concept", "It keeps its source code and takes concept 0, so the fact isn't lost.", "Condition",
     "resource #>> '{code,coding,0,code}' = '62106007'"),
    ("A billing record", "Claims are left out of OMOP, with a recorded reason.", "Claim", "true"),
]
KEEP_OUT = {"meta", "text", "identifier"}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
        cur.execute(CONCEPTS)
        names = [d.name for d in cur.description]
        concepts = [dict(zip(names, row)) for row in cur.fetchall()]
        samples = []
        for title, note, resource_type, where in SAMPLES:
            cur.execute(f"""SELECT resource FROM raw.fhir_resource WHERE resource_type = %s AND {where}
                            ORDER BY resource_id LIMIT 1""", (resource_type,))
            row = cur.fetchone()
            if row is None:
                raise SystemExit(f"no example found for {title}")
            samples.append({"title": title, "note": note,
                            "resource": {k: v for k, v in row[0].items() if k not in KEEP_OUT}})
        cur.execute("SELECT resource_type, disposition, destination, reason FROM reference.resource_disposition ORDER BY 1")
        dispositions = [dict(zip(("resource_type", "disposition", "destination", "reason"), r)) for r in cur.fetchall()]
        cur.execute("SELECT resource_type, raw_rows, disposition, rows_in_omop FROM intermediate.int_resource_accounting ORDER BY raw_rows DESC")
        accounting = [dict(zip(("resource_type", "raw_rows", "disposition", "rows_in_omop"), r)) for r in cur.fetchall()]
        cur.execute(ROUTING)
        routing = [dict(zip(("source_table", "omop_table", "rows"), r)) for r in cur.fetchall()]
        cur.execute(MAPPING)
        mapping = [dict(zip(("source_table", "codes", "codes_ok", "rows", "rows_ok"), r)) for r in cur.fetchall()]
        cur.execute(UNMAPPED)
        unmapped = [dict(zip(("source_table", "code", "display", "status", "rows"), r)) for r in cur.fetchall()]
        cur.execute("SELECT class_code, count(*) FROM staging.stg_encounter GROUP BY 1 ORDER BY 2 DESC")
        visits = [dict(zip(("class_code", "visits"), r)) for r in cur.fetchall()]
    commit = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, cwd=OUT).stdout.strip()
    eda = {"source": {"repo": "https://github.com/michizler/fhir-to-omop", "commit": commit,
                      "note": "Read from the Postgres tables built by this repo from 1,133 Synthea patients, seed 42."},
           "routing": routing, "mapping": mapping, "unmapped": unmapped, "visits": visits, "accounting": accounting}
    (OUT / "eda.json").write_text(json.dumps(eda, indent=1, ensure_ascii=False, default=int), encoding="utf-8")
    (OUT / "concepts.json").write_text(json.dumps(concepts, indent=0, ensure_ascii=False), encoding="utf-8")
    (OUT / "samples.json").write_text(json.dumps(samples, indent=1, ensure_ascii=False), encoding="utf-8")
    (OUT / "dispositions.json").write_text(json.dumps({"dispositions": dispositions, "accounting": accounting}, indent=1), encoding="utf-8")
    print(f"{len(concepts)} concepts, {len(samples)} samples, {len(dispositions)} dispositions")


if __name__ == "__main__":
    main()
