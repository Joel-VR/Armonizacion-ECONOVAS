"""Normalización mínima de CSV FIRMS; no armoniza sensores."""
import argparse
from pathlib import Path
import pandas as pd

def normalize(source: Path, destination: Path, sensor: str) -> None:
    df = pd.read_csv(source, dtype={"acq_time": "string"})
    required = {"latitude", "longitude", "acq_date", "acq_time"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas: {sorted(missing)}")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="raise")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="raise")
    if not df["latitude"].between(-90, 90).all() or not df["longitude"].between(-180, 180).all():
        raise ValueError("Coordenadas fuera de rango o ausentes")
    times = df["acq_time"].str.strip().str.zfill(4)
    df["acquired_at_utc"] = pd.to_datetime(df["acq_date"].astype(str) + " " + times, format="%Y-%m-%d %H%M", utc=True, errors="raise").dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df["sensor"] = sensor
    destination.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(destination, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--sensor", required=True, choices=["MODIS", "VIIRS"])
    args = parser.parse_args()
    normalize(args.source, args.destination, args.sensor)
