"""Step 2 - SESNSP (police / prosecutors): IPV-relevant crimes, old methodology 2015-2025.

Input : carpetas_estatal_2015_2025 and victimas_2015_2025 (state level, monthly), via the manifest.
Output: data/interim/sesnsp/sesnsp_<year>_states.csv  (32 states, one year)
        data/interim/sesnsp/sesnsp_trend_2015_2025.csv (state x year, same measures)

What this source can and cannot give (see docs/coverage.csv):
- CARPETAS (investigation files) count cases, not people, and have no sex or age.
  'Violencia familiar' is the closest police category to IPV but also covers
  other relatives, so it is an upper bound for partner violence, all ages and sexes.
- VICTIMS by sex and age exist only for some crimes (femicide, homicide, lesiones,
  ...), NOT for violencia familiar, and age is only minors (0-17) / adults (18+).
  So women 18+ is possible for those crimes; women 15+ is not possible at all.
- From January 2026 the new RNID methodology replaces this series; it is not
  comparable and is handled separately.

Usage:  python -m src.filter.sesnsp --year 2024
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from src.filter import common

OUT_DIR = common.INTERIM / "sesnsp"
MONTHS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
          "Septiembre", "Octubre", "Noviembre", "Diciembre"]
FIRST_YEAR, LAST_YEAR = 2015, 2025

# Carpetas (cases). key -> (column, values). Every rule is listed in docs/ipv_crosswalk.csv.
CARPETAS = {
    "violencia_familiar": ("Tipo de delito", ["Violencia familiar"]),
    "violencia_genero_no_familiar": (
        "Tipo de delito",
        ["Violencia de género en todas sus modalidades distinta a la violencia familiar"]),
    "feminicidio": ("Tipo de delito", ["Feminicidio"]),
    "violacion": ("Tipo de delito", ["Violación simple", "Violación equiparada"]),
    "abuso_sexual": ("Tipo de delito", ["Abuso sexual"]),
    "acoso_hostigamiento_sexual": ("Tipo de delito", ["Acoso sexual", "Hostigamiento sexual"]),
    "lesiones_dolosas": ("Subtipo de delito", ["Lesiones dolosas"]),
}
# Victims (people) - only crimes the victims file covers.
VICTIMAS = {
    "feminicidio": ("Tipo de delito", ["Feminicidio"]),
    "homicidio_doloso": ("Subtipo de delito", ["Homicidio doloso"]),
    "lesiones_dolosas": ("Subtipo de delito", ["Lesiones dolosas"]),
}
AGE = {"Adultos (18 y más)": "18plus", "Menores de edad (0-17)": "minors",
       "No especificado": "age_unknown", "No identificado": "age_unknown"}


def load(dataset: str) -> pd.DataFrame:
    path = common.raw_file("sesnsp", dataset, f"{FIRST_YEAR}-{LAST_YEAR}")
    df = common.read_zip_csv(path, ".csv")
    missing = {"Año", "Clave_Ent", *MONTHS} - set(df.columns)
    if missing:
        raise SystemExit(f"{dataset}: columns missing {sorted(missing)}")
    df["cve_ent"] = df["Clave_Ent"].astype(int).astype(str).str.zfill(2)
    df[MONTHS] = df[MONTHS].apply(pd.to_numeric, errors="coerce")
    df["total"] = df[MONTHS].sum(axis=1, min_count=1)
    df["n_months"] = df[MONTHS].notna().sum(axis=1)
    return df


def select(df: pd.DataFrame, rules: dict, label: str) -> pd.DataFrame:
    """Tag rows with their category; fail loudly if a rule matches nothing (renamed crime)."""
    parts = []
    for key, (col, values) in rules.items():
        hit = df[df[col].isin(values)]
        if hit.empty:
            raise SystemExit(f"{label}: no rows for {key} ({col} in {values}). "
                             f"Has SESNSP renamed the category?")
        parts.append(hit.assign(category=key))
    return pd.concat(parts, ignore_index=True)


def carpetas_table(c: pd.DataFrame) -> pd.DataFrame:
    sel = select(c, CARPETAS, "carpetas")
    t = sel.pivot_table(index=["cve_ent", "Año"], columns="category", values="total",
                        aggfunc="sum").add_prefix("carpetas_")
    months = sel[sel["category"] == "violencia_familiar"].groupby(["cve_ent", "Año"])["n_months"].min()
    t["carpetas_months_reported"] = months
    return t


def victimas_table(v: pd.DataFrame) -> pd.DataFrame:
    sel = select(v, VICTIMAS, "victimas")
    sel = sel[sel["Sexo"] == "Mujer"].assign(age=lambda d: d["Rango de edad"].map(AGE))
    if sel["age"].isna().any():
        raise SystemExit(f"Unknown age labels: {sel.loc[sel['age'].isna(), 'Rango de edad'].unique()}")
    t = sel.pivot_table(index=["cve_ent", "Año"], columns=["category", "age"], values="total",
                        aggfunc="sum")
    t.columns = [f"women_{age}_{cat}" for cat, age in t.columns]
    return t


def build() -> pd.DataFrame:
    trend = carpetas_table(load("carpetas_estatal_2015_2025")).join(
        victimas_table(load("victimas_2015_2025")), how="outer").reset_index()
    trend = trend.rename(columns={"Año": "year"})
    trend.insert(1, "nom_ent", trend["cve_ent"].map(common.STATES))
    if trend["nom_ent"].isna().any():
        raise SystemExit(f"Unknown state keys: {trend.loc[trend['nom_ent'].isna(), 'cve_ent'].unique()}")
    return trend.sort_values(["year", "cve_ent"]).reset_index(drop=True)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Step 2: SESNSP IPV-relevant crimes (2015-2025 series)")
    p.add_argument("--year", type=int, default=2024)
    args = p.parse_args(argv)
    if not FIRST_YEAR <= args.year <= LAST_YEAR:
        raise SystemExit(f"The old-methodology series covers {FIRST_YEAR}-{LAST_YEAR}. "
                         f"From 2026 use the RNID data (not built yet).")

    trend = build()
    year = trend[trend["year"] == args.year].drop(columns="year")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    y_path = OUT_DIR / f"sesnsp_{args.year}_states.csv"
    t_path = OUT_DIR / f"sesnsp_trend_{FIRST_YEAR}_{LAST_YEAR}.csv"
    year.to_csv(y_path, index=False)
    trend.to_csv(t_path, index=False)

    nat = year.sum(numeric_only=True)
    incomplete = year.loc[year["carpetas_months_reported"] < 12, "nom_ent"].tolist()
    print(f"SESNSP {args.year}: {len(year)} states, old methodology (cases and victims)")
    for m in ["carpetas_violencia_familiar", "carpetas_violencia_genero_no_familiar",
              "carpetas_feminicidio", "carpetas_violacion", "carpetas_lesiones_dolosas",
              "women_18plus_feminicidio", "women_age_unknown_feminicidio",
              "women_18plus_lesiones_dolosas", "women_age_unknown_lesiones_dolosas"]:
        print(f"  {m:40} {nat[m]:>10,.0f}")
    print(f"  states with <12 months reported: {incomplete or 'none'}")
    print("  note: violencia familiar has no sex/age split before 2026 (see docs/coverage.csv)")
    print(f"\nWrote {y_path.relative_to(common.core.ROOT)} and {t_path.relative_to(common.core.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
