CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS fire_detections (
 id bigserial PRIMARY KEY, fingerprint text NOT NULL UNIQUE,
 latitude double precision NOT NULL CHECK(latitude BETWEEN -90 AND 90),
 longitude double precision NOT NULL CHECK(longitude BETWEEN -180 AND 180),
 geom geometry(Point,4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude,latitude),4326)) STORED,
 acquired_at timestamptz NOT NULL, sensor text NOT NULL CHECK(sensor IN ('MODIS','VIIRS')),
 satellite text NOT NULL, confidence text, frp double precision, brightness double precision,
 bright_t31 double precision, scan double precision, track double precision, daynight text,
 fire_type text, version text NOT NULL, source_kind text NOT NULL CHECK(source_kind IN ('archive','nrt')),
 source_file text NOT NULL
);
CREATE INDEX IF NOT EXISTS fire_detections_time_idx ON fire_detections(acquired_at);
CREATE INDEX IF NOT EXISTS fire_detections_geom_idx ON fire_detections USING gist(geom);
CREATE INDEX IF NOT EXISTS fire_detections_sensor_time_idx ON fire_detections(sensor,acquired_at);
