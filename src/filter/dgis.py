"""Step 2 - DGIS health records: women 15+/18+ treated for injuries/violence by a partner.

Input : Lesiones_<year>.zip (D_Evento.txt + D_TipoViolencia.txt), via the manifest.
Codes : config/dgis_codes.yaml (verified against the 2024 coding manual).
Output: data/interim/dgis/dgis_<year>_states.csv (32 states)

What this source can and cannot give (see docs/coverage.csv):
- One row per ATTENTION, not per woman: a woman treated twice counts twice, and
  there is no person ID to de-duplicate. Counts are attentions.
- Sex and single-year age are recorded, so women 15+ and 18+ are exact.
- IPV-specific: intentionality = family violence AND aggressor = spouse/partner/
  boyfriend(girlfriend). Family-violence records with no relationship recorded are
  counted separately so the partner count can be read as a lower bound.
- Coverage is mainly Secretaría de Salud and IMSS-Bienestar units (CLUES 'SSA'/'IMB');
  IMSS-ordinario, ISSSTE and private providers are largely absent.
- State = state of the health unit (CLUES prefix), i.e. where the case was recorded.

Usage:  python -m src.filter.dgis --year 2024
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd
import yaml

from src.filter import common

CODES_PATH = common.core.ROOT / "config" / "dgis_codes.yaml"
OUT_DIR = common.INTERIM / "dgis"
EVENT_COLS = ["ID", "Clues", "CVEEDAD", "Edad", "SEXO", "CodEstado", "CodIntencionalidad",
              "CodParentescoAgresor", "CodMP", "Anio_Estadistico"]


def load_codes() -> dict:
    with open(CODES_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load(year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    path = common.raw_file("dgis", "lesiones_microdatos", year)
    ev = common.read_zip_csv(path, "D_Evento.txt", sep="|", dtype=str, usecols=EVENT_COLS)
    tv = common.read_zip_csv(path, "D_TipoViolencia.txt", sep="|", dtype=str,
                             usecols=["ID", "CodTipoViolencia"])
    ev = ev.apply(lambda s: s.str.strip())
    tv = tv.apply(lambda s: s.str.strip())
    return ev, tv


def flag(ev: pd.DataFrame, tv: pd.DataFrame, year: int, codes: dict) -> pd.DataFrame:
    """One row per attention with 0/1 flags for every inclusion rule."""
    other_years = ev["Anio_Estadistico"] != str(year)
    if other_years.any():
        print(f"  dropping {other_years.sum()} records with Anio_Estadistico != {year}")
        ev = ev[~other_years]
    st = codes["clues_estado"]
    ev = ev.assign(cve_ent=ev["Clues"].str[:2].map(st))
    if ev["cve_ent"].isna().any():
        bad = ev.loc[ev["cve_ent"].isna(), "Clues"].str[:2].value_counts().to_dict()
        raise SystemExit(f"Unknown CLUES state prefixes: {bad} - add them to dgis_codes.yaml")

    edad = pd.to_numeric(ev["Edad"], errors="coerce")
    years = ev["CVEEDAD"] == codes["cveedad"]["anios"]
    age_unknown = (ev["CVEEDAD"] == codes["cveedad"]["desconocida"]) | (ev["Edad"] == codes["edad_desconocida"])
    f = pd.DataFrame({"ID": ev["ID"], "cve_ent": ev["cve_ent"], "clues": ev["Clues"],
                      "cod_estado": ev["CodEstado"]})
    f["mujer"] = ev["SEXO"] == codes["sexo"]["mujer"]
    f["age15"] = years & (edad >= 15) & ~age_unknown
    f["age18"] = years & (edad >= 18) & ~age_unknown
    f["age_unknown"] = age_unknown
    f["vf"] = ev["CodIntencionalidad"] == codes["intencionalidad"]["violencia_familiar"]
    f["vnf"] = ev["CodIntencionalidad"] == codes["intencionalidad"]["violencia_no_familiar"]
    f["partner"] = f["vf"] & (ev["CodParentescoAgresor"] == codes["parentesco"]["pareja"])
    f["rel_unknown"] = f["vf"] & ev["CodParentescoAgresor"].isin(codes["parentesco"]["no_especificado"])
    f["mp"] = ev["CodMP"] == codes["aviso_mp"]["si"]
    for name, code in codes["tipo_violencia"].items():
        f[f"tv_{name}"] = f["ID"].isin(tv.loc[tv["CodTipoViolencia"] == code, "ID"])
    return f


def to_states(f: pd.DataFrame, codes: dict) -> pd.DataFrame:
    w = f[f["mujer"]]
    measures = {
        "women_15plus_violencia_familiar": w["age15"] & w["vf"],
        "women_18plus_violencia_familiar": w["age18"] & w["vf"],
        "women_15plus_violencia_no_familiar": w["age15"] & w["vnf"],
        "women_15plus_partner": w["age15"] & w["partner"],
        "women_18plus_partner": w["age18"] & w["partner"],
        "women_age_unknown_partner": w["age_unknown"] & w["partner"],
        "women_15plus_vf_relationship_unknown": w["age15"] & w["rel_unknown"],
        "women_15plus_partner_aviso_mp": w["age15"] & w["partner"] & w["mp"],
        "women_18plus_partner_aviso_mp": w["age18"] & w["partner"] & w["mp"],
    }
    for name in codes["tipo_violencia"]:
        measures[f"women_15plus_partner_{name}"] = w["age15"] & w["partner"] & w[f"tv_{name}"]
    t = pd.DataFrame(measures).assign(cve_ent=w["cve_ent"]).groupby("cve_ent").sum()
    t.insert(0, "n_units_reporting", f.groupby("cve_ent")["clues"].nunique())
    t.insert(1, "records_all", f.groupby("cve_ent").size())
    # partner share among women 15+ family-violence records WITH a relationship recorded
    known = t["women_15plus_violencia_familiar"] - t["women_15plus_vf_relationship_unknown"]
    t["share_partner_of_vf_known_rel_15plus"] = t["women_15plus_partner"] / known.where(known > 0)
    out = common.state_frame().merge(t.reset_index(), on="cve_ent", how="left")
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Step 2: DGIS partner-violence attentions, women 15+/18+")
    p.add_argument("--year", type=int, default=2024)
    args = p.parse_args(argv)

    codes = load_codes()
    ev, tv = load(args.year)
    f = flag(ev, tv, args.year, codes)
    states = to_states(f, codes)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"dgis_{args.year}_states.csv"
    states.to_csv(path, index=False)

    nat = states.sum(numeric_only=True)
    agree = (f["cve_ent"] == f["cod_estado"]).mean()
    print(f"DGIS {args.year}: {len(f):,} attentions from {f['clues'].nunique():,} units "
          f"(CLUES: {f['clues'].str[2:5].value_counts().head(3).to_dict()})")
    for m in ["women_15plus_violencia_familiar", "women_15plus_partner", "women_18plus_partner",
              "women_age_unknown_partner", "women_15plus_vf_relationship_unknown",
              "women_15plus_partner_aviso_mp", "women_15plus_partner_fisica",
              "women_15plus_partner_sexual", "women_15plus_partner_psicologica"]:
        print(f"  {m:40} {nat[m]:>10,.0f}")
    known = nat["women_15plus_violencia_familiar"] - nat["women_15plus_vf_relationship_unknown"]
    print(f"  partner share of family-violence records (women 15+, known relationship): "
          f"{nat['women_15plus_partner'] / known:.1%}")
    print(f"  facility state = CodEstado for {agree:.1%} of records")
    print(f"\nWrote {path.relative_to(common.core.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
