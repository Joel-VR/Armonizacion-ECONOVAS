-- Additive migration: original fire_detections rows are never changed or deleted.
CREATE TABLE IF NOT EXISTS reference_layers (
 id text PRIMARY KEY,
 provider text NOT NULL,
 collection text NOT NULL,
 reference_year integer NOT NULL,
 source_url text NOT NULL,
 license text NOT NULL,
 native_crs text NOT NULL,
 checksum_sha256 text NOT NULL,
 metadata jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS observation_evaluations (
 observation_id bigint NOT NULL REFERENCES fire_detections(id),
 layer_id text NOT NULL REFERENCES reference_layers(id),
 rule_version text NOT NULL,
 cover_code integer NOT NULL,
 cover_category text NOT NULL CHECK (cover_category IN ('forest','agriculture','water','urban','other','unknown')),
 decision text NOT NULL CHECK (decision IN ('candidate','review','excluded')),
 reason text NOT NULL,
 evaluated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY (observation_id,layer_id,rule_version)
);
CREATE INDEX IF NOT EXISTS observation_evaluations_decision_idx
 ON observation_evaluations(decision,cover_category,observation_id);
