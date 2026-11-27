"""Shared helpers for Step 2 filters: raw-file lookup, state keys, zip reading."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

from src.acquire import core

INTERIM = core.ROOT / "data" / "interim"

# INEGI state keys (cve_ent) -> short names, used to label every output
STATES = {
    "01": "Aguascalientes", "02": "Baja California", "03": "Baja California Sur",
    "04": "Campeche", "05": "Coahuila", "06": "Colima", "07": "Chiapas", "08": "Chihuahua",
    "09": "Ciudad de México", "10": "Durango", "11": "Guanajuato", "12": "Guerrero",
    "13": "Hidalgo", "14": "Jalisco", "15": "México", "16": "Michoacán", "17": "Morelos",
    "18": "Nayarit", "19": "Nuevo León", "20": "Oaxaca", "21": "Puebla", "22": "Querétaro",
    "23": "Quintana Roo", "24": "San Luis Potosí", "25": "Sinaloa", "26": "Sonora",
    "27": "Tabasco", "28": "Tamaulipas", "29": "Tlaxcala", "30": "Veracruz", "31": "Yucatán",
    "32": "Zacatecas",
}


def raw_file(source: str, dataset: str, key: str | int) -> Path:
    """Path of the current raw file for a manifest slot, or a clear error."""
    row = core.Manifest().latest(source, dataset, key)
    if not row:
        raise SystemExit(f"{source}/{dataset} ({key}) is not in data/raw/manifest.csv. "
                         f"Run step 1 (python -m src.acquire run) or register the file.")
    path = core.ROOT / row["file"]
    if not path.exists():
        raise SystemExit(f"Manifest lists {row['file']} but the file is missing.")
    return path


def read_zip_csv(zip_path: Path, member_endswith: str, **kw) -> pd.DataFrame:
    """Read one CSV/TXT inside a zip without extracting it (raw stays untouched)."""
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if n.endswith(member_endswith)]
        if len(names) != 1:
            raise SystemExit(f"Expected one member ending '{member_endswith}' in {zip_path.name}, "
                             f"found {names}")
        raw = z.read(names[0])
    enc = kw.pop("encoding", None)
    for e in ([enc] if enc else ["utf-8-sig", "latin-1"]):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=e, low_memory=False, **kw)
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"Could not decode {names[0]}")


def state_frame() -> pd.DataFrame:
    return pd.DataFrame({"cve_ent": list(STATES), "nom_ent": list(STATES.values())})
