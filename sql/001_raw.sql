-- Raw layer: one row per FHIR bundle entry, exactly as published, plus an audit row per file.
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.fhir_resource (
    source_file   text    NOT NULL,
    entry_index   integer NOT NULL,
    resource_type text    NOT NULL,
    resource_id   text    NOT NULL,
    patient_id    text,               -- NULL for the shared hospital and practitioner files
    resource      jsonb   NOT NULL,
    PRIMARY KEY (source_file, entry_index)
);
CREATE INDEX IF NOT EXISTS fhir_resource_type_idx ON raw.fhir_resource (resource_type);

CREATE TABLE IF NOT EXISTS raw.load_audit (
    source_file       text PRIMARY KEY,
    sha256            text        NOT NULL,
    entries_in_file   integer     NOT NULL,
    entries_loaded    integer     NOT NULL,
    loaded_at         timestamptz NOT NULL DEFAULT now()
);
