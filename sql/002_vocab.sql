-- Vocabulary layer: the parts of the Athena download this project uses, plus how many rows each file gave.
CREATE SCHEMA IF NOT EXISTS vocab;

CREATE TABLE IF NOT EXISTS vocab.concept (
    concept_id       integer PRIMARY KEY,
    concept_name     text    NOT NULL,
    domain_id        text    NOT NULL,
    vocabulary_id    text    NOT NULL,
    concept_class_id text    NOT NULL,
    standard_concept text,
    concept_code     text    NOT NULL,
    valid_start_date date    NOT NULL,
    valid_end_date   date    NOT NULL,
    invalid_reason   text
);

CREATE TABLE IF NOT EXISTS vocab.concept_relationship (
    concept_id_1     integer NOT NULL,
    concept_id_2     integer NOT NULL,
    relationship_id  text    NOT NULL,
    valid_start_date date    NOT NULL,
    valid_end_date   date    NOT NULL,
    invalid_reason   text
);

CREATE TABLE IF NOT EXISTS vocab.vocabulary_version (
    vocabulary_id   text PRIMARY KEY,
    vocabulary_name text,
    vocabulary_version text
);

CREATE TABLE IF NOT EXISTS vocab.load_audit (
    source_file text PRIMARY KEY,
    rows_read   bigint NOT NULL,
    rows_loaded bigint NOT NULL,
    loaded_at   timestamptz NOT NULL DEFAULT now()
);
