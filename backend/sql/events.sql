-- Additive, versioned model. Raw NASA observations remain immutable.
CREATE TABLE IF NOT EXISTS paises (
 codigo text PRIMARY KEY, nombre text NOT NULL
);
CREATE TABLE IF NOT EXISTS departamentos (
 codigo text PRIMARY KEY, pais_codigo text NOT NULL REFERENCES paises(codigo),
 nombre text NOT NULL, limite geometry(Geometry,4326) NOT NULL
);
CREATE TABLE IF NOT EXISTS provincias (
 codigo text PRIMARY KEY, departamento_codigo text NOT NULL REFERENCES departamentos(codigo),
 nombre text NOT NULL, limite geometry(MultiPolygon,4326)
);
CREATE TABLE IF NOT EXISTS distritos (
 codigo text PRIMARY KEY, provincia_codigo text NOT NULL REFERENCES provincias(codigo),
 nombre text NOT NULL, limite geometry(MultiPolygon,4326)
);
CREATE TABLE IF NOT EXISTS fuentes_datos (
 id bigserial PRIMARY KEY, archivo text NOT NULL, sensor text NOT NULL,
 satelite text NOT NULL, producto text NOT NULL, modalidad text NOT NULL,
 UNIQUE(archivo,sensor,satelite,producto,modalidad)
);
CREATE TABLE IF NOT EXISTS reglas_procesamiento (
 version text PRIMARY KEY, parametros jsonb NOT NULL, creada_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS ejecuciones_procesamiento (
 id bigserial PRIMARY KEY, regla_version text NOT NULL REFERENCES reglas_procesamiento(version),
 capa_id text NOT NULL REFERENCES reference_layers(id), departamento_codigo text NOT NULL REFERENCES departamentos(codigo),
 iniciada_en timestamptz NOT NULL DEFAULT now(), finalizada_en timestamptz,
 activa boolean NOT NULL DEFAULT false, resumen jsonb NOT NULL DEFAULT '{}'
);
CREATE UNIQUE INDEX IF NOT EXISTS ejecucion_activa_idx ON ejecuciones_procesamiento(departamento_codigo) WHERE activa;
CREATE TABLE IF NOT EXISTS evaluaciones_fuego (
 ejecucion_id bigint NOT NULL REFERENCES ejecuciones_procesamiento(id),
 deteccion_id bigint NOT NULL REFERENCES fire_detections(id),
 fuente_id bigint NOT NULL REFERENCES fuentes_datos(id),
 cobertura_codigo integer NOT NULL, cobertura text NOT NULL,
 resultado text NOT NULL CHECK(resultado IN ('apta','revision','excluida')),
 motivo text NOT NULL, evidencia jsonb NOT NULL,
 PRIMARY KEY(ejecucion_id,deteccion_id)
);
CREATE TABLE IF NOT EXISTS eventos_fuego (
 id bigserial PRIMARY KEY, ejecucion_id bigint NOT NULL REFERENCES ejecuciones_procesamiento(id),
 departamento_codigo text NOT NULL REFERENCES departamentos(codigo),
 distrito_codigo text REFERENCES distritos(codigo),
 tipo text NOT NULL CHECK(tipo IN ('incendio_forestal','quema_agricola','fuego_sin_clasificar')),
 estado text NOT NULL DEFAULT 'probable' CHECK(estado IN ('probable','confirmado','descartado')),
 inicio timestamptz NOT NULL, ultima_deteccion timestamptz NOT NULL,
 representante_id bigint NOT NULL REFERENCES fire_detections(id),
 motivo text NOT NULL, CHECK(ultima_deteccion>=inicio), UNIQUE(id,ejecucion_id)
);
CREATE TABLE IF NOT EXISTS evento_detecciones (
 evento_id bigint NOT NULL REFERENCES eventos_fuego(id),
 ejecucion_id bigint NOT NULL, deteccion_id bigint NOT NULL,
 PRIMARY KEY(evento_id,deteccion_id), UNIQUE(ejecucion_id,deteccion_id),
 FOREIGN KEY(evento_id,ejecucion_id) REFERENCES eventos_fuego(id,ejecucion_id),
 FOREIGN KEY(ejecucion_id,deteccion_id) REFERENCES evaluaciones_fuego(ejecucion_id,deteccion_id)
);
CREATE INDEX IF NOT EXISTS eventos_intervalo_idx ON eventos_fuego(ejecucion_id,inicio,ultima_deteccion);
CREATE INDEX IF NOT EXISTS evaluaciones_resultado_idx ON evaluaciones_fuego(ejecucion_id,resultado);
CREATE INDEX IF NOT EXISTS departamentos_limite_idx ON departamentos USING gist(limite);
