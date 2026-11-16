"""Print an overview of every raw file in the manifest, to plan Step 2 (filtering).

Usage (from the repo root):
    python tools/inspect_raw.py > raw_overview.txt

For each file: size, members (zips), column names, 3 example rows, and the
categories of key columns (sex, age, violence type, aggressor relationship...).
Reads only; changes nothing.
"""

from __future__ import annotations

import csv
import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "raw" / "manifest.csv"

KEY_COLS = re.compile(
    r"(?i)(sexo|sex\b|edad|grupo.?edad|rango|intenc|violen|agresor|parent|relaci|"
    r"tipo|subtipo|delito|modalidad|entidad|ent\b|cve_ent|a[nñ]o|mes|v[ií]nculo|pareja|"
    r"servicio|atenci|ambito|ámbito)")
MAX_CATS = 40
pd.set_option("display.width", 200, "display.max_columns", 60, "display.max_colwidth", 30) # type: ignore


def read_table(raw: bytes, name: str) -> pd.DataFrame | None:
    if name.lower().endswith((".xlsx", ".xls")):
        try:
            return pd.read_excel(io.BytesIO(raw), sheet_name=0, dtype=str)
        except Exception as exc:  # noqa: BLE001
            print(f"    (could not read Excel: {exc}; try: pip install openpyxl)")
            return None
    for enc in ("utf-8-sig", "latin-1"):
        try:
            text = raw.decode(enc)
            sep = csv.Sniffer().sniff(text[:5000], delimiters=",;|\t").delimiter
            return pd.read_csv(io.StringIO(text), sep=sep, dtype=str, low_memory=False)
        except Exception:  # noqa: BLE001
            continue
    print("    (could not parse as CSV)")
    return None


def describe(df: pd.DataFrame, label: str) -> None:
    print(f"  ## {label}: {len(df):,} rows x {df.shape[1]} columns")
    print(f"  columns: {list(df.columns)}")
    print("  example rows:")
    print("   " + df.head(3).to_string(max_cols=40).replace("\n", "\n   "))
    for col in df.columns:
        if not KEY_COLS.search(str(col)):
            continue
        vc = df[col].value_counts(dropna=False)
        if len(vc) > MAX_CATS:
            sample = ", ".join(map(str, vc.index[:12]))
            print(f"  [{col}] {len(vc)} distinct values, most common: {sample} ...")
        else:
            items = ", ".join(f"{k}={v:,}" for k, v in vc.items())
            print(f"  [{col}] {items}")
    print()


def inspect_file(path: Path) -> None:
    size = path.stat().st_size
    print(f"\n=== {path.relative_to(ROOT)}  ({size / 1e6:.1f} MB)")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        print("  (PDF – codebook/report; not parsed)")
        return
    if suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            members = [m for m in z.infolist() if not m.is_dir()]
            print(f"  zip with {len(members)} files:")
            for m in members[:80]:
                print(f"    {m.filename}  ({m.file_size / 1e6:.1f} MB)")
            tables = [m for m in members if m.filename.lower().endswith((".csv", ".txt", ".xlsx"))]
            # ENDIREH-style zips hold dozens of tables: show headers only for those
            headers_only = len(tables) > 6
            for m in tables:
                raw = z.read(m)
                if headers_only:
                    first = raw[:4000].decode("latin-1").splitlines()[0]
                    print(f"  ## {m.filename}: header -> {first[:600]}")
                    continue
                df = read_table(raw, m.filename)
                if df is not None:
                    describe(df, m.filename)
        return
    if suffix in {".csv", ".txt", ".xlsx", ".xls"}:
        df = read_table(path.read_bytes(), path.name)
        if df is not None:
            describe(df, path.name)
        return
    print("  (unknown type; first bytes:)", path.read_bytes()[:80])


def main() -> int:
    if not MANIFEST.exists():
        print("No manifest yet – run step 1 first.")
        return 1
    with open(MANIFEST, encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["status"] == "current"]
    print(f"Raw files in manifest: {len(rows)}")
    for r in rows:
        p = ROOT / r["file"]
        if p.exists():
            try:
                inspect_file(p)
            except Exception as exc:  # noqa: BLE001
                print(f"  ERROR reading {p.name}: {exc}")
        else:
            print(f"\n=== {r['file']}  MISSING ON DISK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
