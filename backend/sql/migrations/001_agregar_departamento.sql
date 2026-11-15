-- Columna derivada: las observaciones originales y sus coordenadas se conservan.
ALTER TABLE public.modis ADD COLUMN IF NOT EXISTS departamento text;
ALTER TABLE public.viirs ADD COLUMN IF NOT EXISTS departamento text;
