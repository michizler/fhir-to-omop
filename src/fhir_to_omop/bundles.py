"""Reads FHIR bundles into plain rows, keeping each resource exactly as published. No database code here."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    index: int
    resource_type: str
    resource_id: str
    patient_id: str | None
    resource_json: str


@dataclass(frozen=True)
class Bundle:
    source_file: str
    sha256: str
    entries: list[Entry]


def parse_bundle(raw: bytes, source_file: str) -> Bundle:
    """One Entry per bundle entry, in file order. A bundle with no Patient is a shared file, so its patient is None.

    A patient bundle must hold exactly one Patient, because every row in it inherits that patient's ID. Two would
    silently give one person's records to the other, so it stops the load instead."""
    doc = json.loads(raw)
    if doc.get("resourceType") != "Bundle":
        raise ValueError(f"{source_file}: not a FHIR Bundle")
    resources = [e["resource"] for e in doc.get("entry", [])]
    patients = [r["id"] for r in resources if r["resourceType"] == "Patient"]
    if len(patients) > 1:
        raise ValueError(f"{source_file}: {len(patients)} Patient resources in one bundle")
    patient_id = patients[0] if patients else None
    entries = [Entry(i, r["resourceType"], r["id"], patient_id, json.dumps(r, separators=(",", ":"), ensure_ascii=False))
               for i, r in enumerate(resources)]
    return Bundle(source_file, hashlib.sha256(raw).hexdigest(), entries)


def bundle_paths(folder: Path) -> list[Path]:
    return sorted(folder.glob("*.json"))
