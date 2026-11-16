"""Step 2 - CJM (Centros de Justicia para las Mujeres): extract IPV-relevant counts.

Input : BD_CJM_<edition>.csv (one row per centre, ~3,800 columns), found via the manifest.
Output: data/interim/cjm/cjm_<year>_centres.csv  (one row per centre)
        data/interim/cjm/cjm_<year>_states.csv   (summed to the 32 states)

What the CJM data can and cannot give (from the 2025 FD codebook):
- Women attended by AGE GROUP (q5.1.9) -> women 15+ and 18+ are exact.
- Violence INCIDENTS by RELATIONSHIP to the aggressor (q5.1.14) -> partner incidents
  (pareja + expareja + novio + novia). These are incidents, not women, all ages.
- The two are NOT cross-tabulated, so "women 15+ attended for IPV" has to be
  estimated: women_15plus x (partner incidents / all incidents). The estimate is
  labelled `est_` and the raw ingredients are kept next to it.
- 'NA' (no aplica) and 'ND' (no disponible) are kept as missing, and every
  state row reports how many centres were missing for each measure.

Usage:  python -m src.filter.cjm --year 2024
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

from src.acquire import core

COLMAP_PATH = core.ROOT / "config" / "cjm_2025_columns.csv"
OUT_DIR = core.ROOT / "data" / "interim" / "cjm"

# Column suffix for the year's TOTAL (FD layout): q5.1.9/13/14 -> _1 = 2023, _5 = 2024;
# q5.1.1 and q5.2.1 -> _1 = 2023, _2 = 2024.
YEAR_SUFFIX_WIDE = {2023: 1, 2024: 5}
YEAR_SUFFIX_NARROW = {2023: 1, 2024: 2}

AGE_GROUPS = {  # q5.1.9 group index -> label (verified against the codebook at run time)
    2: "0-4", 3: "5-9", 4: "10-11", 5: "12-14", 6: "15-17", 7: "18-19", 8: "20-24",
    9: "25-29", 10: "30-34", 11: "35-39", 12: "40-44", 13: "45-49", 14: "50-54",
    15: "55-59", 16: "60+", 17: "no_especificado",
}
AGE_15PLUS = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
AGE_18PLUS = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
PARTNER = {2: "Pareja", 3: "Expareja", 4: "Novio", 5: "Novia"}   # q5.1.14 groups
VIOLENCE_TYPES = {2: "psicologica", 3: "fisica", 4: "sexual", 5: "economica",
                  6: "patrimonial", 7: "interposita", 8: "otra", 9: "no_especificado"}


def load_colmap() -> dict[str, str]:
    with open(COLMAP_PATH, encoding="utf-8") as fh:
        return {r["column"]: r["label"] for r in csv.DictReader(fh)}


def build_spec(year: int, colmap: dict[str, str]) -> dict[str, list[str]]:
    """Map each output measure to its source columns and check labels against the codebook."""
    if year not in YEAR_SUFFIX_WIDE:
        raise SystemExit(f"CJM 2025 edition covers 2023 and 2024 only, not {year}.")
    w, n = YEAR_SUFFIX_WIDE[year], YEAR_SUFFIX_NARROW[year]
    spec: dict[str, list[str]] = {
        "women_total": [f"P5_1_1_1_{n}"],
        "women_first_visit": [f"P5_1_1_2_{n}"],
        "women_age_total": [f"P5_1_9_1_{w}"],
        "women_15plus": [f"P5_1_9_{g}_{w}" for g in AGE_15PLUS],
        "women_18plus": [f"P5_1_9_{g}_{w}" for g in AGE_18PLUS],
        "women_age_unknown": [f"P5_1_9_17_{w}"],
        "incidents_total": [f"P5_1_14_1_{w}"],
        "incidents_partner": [f"P5_1_14_{g}_{w}" for g in PARTNER],
        "incidents_relationship_unknown": [f"P5_1_14_27_{w}"],
        # q5.2.1's "Total" is the total of its own breakdown (incl. women who did NOT
        # report), so women who reported = denuncia + querella.
        "women_reported": [f"P5_2_1_2_{n}", f"P5_2_1_3_{n}"],
        "women_denuncia": [f"P5_2_1_2_{n}"],
        "women_querella": [f"P5_2_1_3_{n}"],
        "women_not_reported": [f"P5_2_1_4_{n}"],
        "women_report_unknown": [f"P5_2_1_5_{n}"],
    }
    for g, name in PARTNER.items():
        spec[f"incidents_{name.lower()}"] = [f"P5_1_14_{g}_{w}"]
    for g, name in VIOLENCE_TYPES.items():
        spec[f"violence_{name}"] = [f"P5_1_13_{g}_{w}"]

    # Guard against a wrong index: every column must exist in the codebook,
    # start with the right year, and age/partner columns must carry the right label.
    problems = []
    for measure, cols in spec.items():
        for c in cols:
            label = colmap.get(c)
            if label is None:
                problems.append(f"{measure}: {c} not in codebook")
            elif not label.startswith(f"{year}."):
                problems.append(f"{measure}: {c} is '{label}', not {year}")
    for g, lab in AGE_GROUPS.items():
        if g == 17:
            continue
        got = colmap.get(f"P5_1_9_{g}_{w}", "")
        first = lab.split("-")[0].rstrip("+")
        if not got.startswith(f"{year}. {first}"):
            problems.append(f"age group {g}: expected '{lab}', codebook says '{got}'")
    for g, lab in PARTNER.items():
        if lab not in colmap.get(f"P5_1_14_{g}_{w}", ""):
            problems.append(f"partner group {g}: expected '{lab}'")
    if problems:
        raise SystemExit("Codebook check failed:\n  " + "\n  ".join(problems))
    return spec


def to_number(s: pd.Series) -> pd.Series:
    """'NA'/'ND'/blank -> missing; everything else numeric."""
    return pd.to_numeric(s.astype(str).str.strip().replace({"NA": None, "ND": None, "": None,
                                                            "nan": None}), errors="coerce")


def find_input() -> Path:
    row = core.Manifest().latest("cjm", "datos_abiertos", "ed2025")
    if not row:
        raise SystemExit("CJM database not in the manifest. Run step 1 / register BD_CJM_2025.csv.")
    return core.ROOT / row["file"]


def read_bd(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, dtype=str, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"Could not decode {path}")


def extract(df: pd.DataFrame, spec: dict[str, list[str]]) -> pd.DataFrame:
    out = df[["ID_CJM", "NOM_CJM", "CVE_ENT", "NOM_ENT"]].copy()
    out["CVE_ENT"] = out["CVE_ENT"].str.zfill(2)
    missing_cols = sorted({c for cols in spec.values() for c in cols} - set(df.columns))
    if missing_cols:
        raise SystemExit(f"Columns missing from the database: {missing_cols[:10]} ...")
    for measure, cols in spec.items():
        vals = df[cols].apply(to_number)
        # Sum the components the centre reported. Missing only if ALL are missing;
        # if some are missing the sum is a lower bound and `<measure>_n_missing` says how many.
        out[measure] = vals.sum(axis=1, min_count=1)
        if len(cols) > 1:
            out[f"{measure}_n_missing"] = vals.isna().sum(axis=1)
    out["share_partner_incidents"] = out["incidents_partner"] / out["incidents_total"]
    # Share among incidents whose relationship WAS recorded (assumes unrecorded look alike)
    known = out["incidents_total"] - out["incidents_relationship_unknown"].fillna(0)
    out["share_partner_known_rel"] = out["incidents_partner"] / known.where(known > 0)
    # Age-adjusted counts: spread 'age not specified' in proportion to known ages
    known_age = out["women_age_total"] - out["women_age_unknown"].fillna(0)
    scale = out["women_age_total"] / known_age.where(known_age > 0)
    out["women_15plus_adj"] = out["women_15plus"] * scale
    out["women_18plus_adj"] = out["women_18plus"] * scale
    out["est_women_15plus_partner"] = out["women_15plus"] * out["share_partner_incidents"]
    out["est_women_18plus_partner"] = out["women_18plus"] * out["share_partner_incidents"]
    return out


def to_states(centres: pd.DataFrame) -> pd.DataFrame:
    measures = [c for c in centres.columns
                if c not in {"ID_CJM", "NOM_CJM", "CVE_ENT", "NOM_ENT", "share_partner_incidents",
                             "share_partner_known_rel"}
                and not c.endswith("_n_missing")]
    g = centres.groupby(["CVE_ENT", "NOM_ENT"])
    states = g[measures].sum(min_count=1)
    states.insert(0, "n_centres", g.size())
    for m in ["women_15plus", "incidents_partner", "incidents_total"]:
        states[f"n_centres_missing_{m}"] = g[m].agg(lambda s: int(s.isna().sum()))
    # share computed only over centres that report BOTH partner and total incidents
    both = centres.dropna(subset=["incidents_partner", "incidents_total"])
    gb = both.groupby(["CVE_ENT", "NOM_ENT"])[["incidents_partner", "incidents_total"]].sum()
    states["share_partner_incidents"] = gb["incidents_partner"] / gb["incidents_total"]
    both = both.assign(_known=both["incidents_total"] - both["incidents_relationship_unknown"].fillna(0))
    gk = both.groupby(["CVE_ENT", "NOM_ENT"])[["incidents_partner", "_known"]].sum()
    states["share_partner_known_rel"] = gk["incidents_partner"] / gk["_known"].where(gk["_known"] > 0)
    return states.reset_index()


def national_share(centres: pd.DataFrame, known_rel: bool = False) -> tuple[float, int]:
    both = centres.dropna(subset=["incidents_partner", "incidents_total"])
    denom = both["incidents_total"]
    if known_rel:
        denom = denom - both["incidents_relationship_unknown"].fillna(0)
    keep = denom > 0
    return both.loc[keep, "incidents_partner"].sum() / denom[keep].sum(), int(keep.sum())


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Step 2: CJM counts for adult women / IPV")
    p.add_argument("--year", type=int, default=2024)
    args = p.parse_args(argv)

    spec = build_spec(args.year, load_colmap())
    src = find_input()
    centres = extract(read_bd(src), spec)
    states = to_states(centres)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    c_path = OUT_DIR / f"cjm_{args.year}_centres.csv"
    s_path = OUT_DIR / f"cjm_{args.year}_states.csv"
    centres.to_csv(c_path, index=False)
    states.to_csv(s_path, index=False)

    nat = states.sum(numeric_only=True)
    print(f"CJM {args.year}: {len(centres)} centres in {states['CVE_ENT'].nunique()} states  (source: {src.name})")
    for m in ["women_total", "women_15plus", "women_15plus_adj", "women_18plus", "women_age_unknown",
              "incidents_total", "incidents_partner", "est_women_15plus_partner",
              "women_reported", "women_not_reported"]:
        n_miss = int(centres[m].isna().sum())
        partial = (f", {int((centres[m + '_n_missing'] > 0).sum() - n_miss)} partial"
                   if m + "_n_missing" in centres else "")
        print(f"  {m:28} {nat[m]:>12,.0f}   ({n_miss} centres missing{partial})")
    share, n = national_share(centres)
    print(f"  share of incidents by a partner: {share:.1%}  (over {n} centres reporting both)")
    share_k, n_k = national_share(centres, known_rel=True)
    print(f"  ... among incidents with relationship recorded: {share_k:.1%}  (over {n_k} centres)")
    print(f"\nWrote {c_path.relative_to(core.ROOT)} and {s_path.relative_to(core.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
