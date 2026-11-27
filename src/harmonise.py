"""Step 4 - Line up every source in one table: state x year x age group (long format).

Input : the Step 2 outputs in data/interim/<source>/.
Output: data/processed/tabla_armonizada_<years>[_<state>].csv

One row = one count from one source, for one state, year and age group. Nothing is
adjusted, averaged or converted: each row keeps its own unit (cases, victims, women
attended, incidents, attentions, women interviewed, estimated women), so the table
shows what each institution actually records. Decisions are in docs/decisions.md
(2026-11-27, "Tabla armonizada").

Usage:  python -m src.harmonise --years 2024 2025 --state 09   # one state (prototype)
        python -m src.harmonise --years 2024 2025              # all states
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from src.filter import common

OUT_DIR = common.core.ROOT / "data" / "processed"
ENDIREH_EDITION = 2021
LOW_N = 30  # fewer women interviewed than this -> flag (INEGI's precision rule also uses CV > 30%)

AGE = {"15plus": "15+", "18plus": "18+", "all": "todas", "unknown": "edad no registrada"}

# (column in the Step 2 output, age group, unit, relationship to aggressor, description)
SESNSP = [
    ("carpetas_violencia_familiar", "all", "carpetas", "familiar (incluye pareja)",
     "Carpetas por violencia familiar (cualquier sexo)"),
    ("carpetas_violencia_genero_no_familiar", "all", "carpetas", "no familiar",
     "Carpetas por violencia de género distinta a la familiar"),
    ("carpetas_feminicidio", "all", "carpetas", "no registrada", "Carpetas por feminicidio"),
    ("carpetas_violacion", "all", "carpetas", "no registrada",
     "Carpetas por violación (cualquier sexo)"),
    ("women_18plus_feminicidio", "18plus", "víctimas mujeres", "no registrada",
     "Mujeres víctimas de feminicidio"),
    ("women_age_unknown_feminicidio", "unknown", "víctimas mujeres", "no registrada",
     "Mujeres víctimas de feminicidio"),
    ("women_18plus_homicidio_doloso", "18plus", "víctimas mujeres", "no registrada",
     "Mujeres víctimas de homicidio doloso"),
    ("women_age_unknown_homicidio_doloso", "unknown", "víctimas mujeres", "no registrada",
     "Mujeres víctimas de homicidio doloso"),
    ("women_18plus_lesiones_dolosas", "18plus", "víctimas mujeres", "no registrada",
     "Mujeres víctimas de lesiones dolosas"),
    ("women_age_unknown_lesiones_dolosas", "unknown", "víctimas mujeres", "no registrada",
     "Mujeres víctimas de lesiones dolosas"),
]
CJM = [
    ("women_total", "all", "mujeres atendidas", "cualquiera", "Mujeres atendidas en CJM"),
    ("women_15plus", "15plus", "mujeres atendidas", "cualquiera", "Mujeres atendidas en CJM"),
    ("women_18plus", "18plus", "mujeres atendidas", "cualquiera", "Mujeres atendidas en CJM"),
    ("women_age_unknown", "unknown", "mujeres atendidas", "cualquiera", "Mujeres atendidas en CJM"),
    ("incidents_total", "all", "incidentes", "cualquiera", "Incidentes de violencia registrados en CJM"),
    ("incidents_partner", "all", "incidentes", "pareja o expareja",
     "Incidentes de violencia registrados en CJM"),
    ("incidents_relationship_unknown", "all", "incidentes", "no registrada",
     "Incidentes de violencia registrados en CJM"),
    ("women_reported", "all", "mujeres atendidas", "cualquiera",
     "Mujeres atendidas en CJM que presentaron denuncia o querella"),
]
DGIS = [
    ("women_15plus_violencia_familiar", "15plus", "atenciones", "familiar (incluye pareja)",
     "Atenciones a mujeres por violencia familiar"),
    ("women_18plus_violencia_familiar", "18plus", "atenciones", "familiar (incluye pareja)",
     "Atenciones a mujeres por violencia familiar"),
    ("women_15plus_partner", "15plus", "atenciones", "pareja", "Atenciones a mujeres por violencia de pareja"),
    ("women_18plus_partner", "18plus", "atenciones", "pareja", "Atenciones a mujeres por violencia de pareja"),
    ("women_age_unknown_partner", "unknown", "atenciones", "pareja",
     "Atenciones a mujeres por violencia de pareja"),
    ("women_15plus_vf_relationship_unknown", "15plus", "atenciones", "no registrada",
     "Atenciones a mujeres por violencia familiar"),
    ("women_15plus_partner_aviso_mp", "15plus", "atenciones", "pareja",
     "Atenciones por violencia de pareja con aviso al Ministerio Público"),
    ("women_18plus_partner_aviso_mp", "18plus", "atenciones", "pareja",
     "Atenciones por violencia de pareja con aviso al Ministerio Público"),
]
# ENDIREH indicator -> (relationship, description). Each gives two rows: women interviewed
# (raw count) and estimated women (INEGI expansion factors).
ENDIREH = [
    ("ipv_12m", "pareja", "Mujeres con violencia de pareja en los últimos 12 meses"),
    ("ipv_life_ever_partnered", "pareja", "Mujeres con violencia de pareja en su relación actual o última"),
    ("sought_or_complaint", "pareja",
     "… de ellas, pidieron apoyo a una institución o denunciaron"),
    ("complaint_police_or_mp", "pareja", "… de ellas, denunciaron ante policía o Ministerio Público"),
    ("sought_cjm", "pareja", "… de ellas, pidieron apoyo a un CJM"),
    ("sought_health_public", "pareja", "… de ellas, pidieron apoyo a un servicio de salud público"),
]


def _rows(df, key, state_name, year, sector, source, spec, path):
    out = []
    for _, r in df.iterrows():
        for col, age, unit, rel, desc in spec:
            out.append({"cve_ent": r[key], "nom_ent": common.STATES[r[key]], "anio": year,
                        "sector": sector, "fuente": source, "indicador": col,
                        "descripcion": desc, "grupo_edad": AGE[age], "relacion_agresor": rel,
                        "unidad": unit, "valor": r.get(col), "precision_baja": "",
                        "archivo_origen": path})
    return out


def _read(path, key):
    p = common.core.ROOT / path
    if not p.exists():
        return None
    return pd.read_csv(p, dtype={key: str})


def build(years: list[int], state: str | None) -> tuple[pd.DataFrame, list[str]]:
    rows, missing = [], []
    pick = (lambda d, k: d[d[k] == state]) if state else (lambda d, k: d)
    for y in years:
        f = "data/interim/sesnsp/sesnsp_trend_2015_2025.csv"
        d = _read(f, "cve_ent")
        if d is None or y not in set(d["year"]):
            missing.append(f"Policía {y}: no disponible en la serie 2015–2025")
        else:
            rows += _rows(pick(d[d["year"] == y], "cve_ent"), "cve_ent", None, y,
                          "Policía y fiscalías", "SESNSP", SESNSP, f)
        f = f"data/interim/cjm/cjm_{y}_states.csv"
        d = _read(f, "CVE_ENT")
        if d is None:
            missing.append(f"CJM {y}: sin archivo (la edición 2025 cubre 2023 y 2024)")
        else:
            # sum duplicate state keys (one centre has a mismatched state name; see GUIDE)
            d = d.groupby("CVE_ENT", as_index=False).sum(numeric_only=True, min_count=1)
            rows += _rows(pick(d, "CVE_ENT"), "CVE_ENT", None, y,
                          "Centros de Justicia para las Mujeres", "INEGI CJM 2025", CJM, f)
        f = f"data/interim/dgis/dgis_{y}_states.csv"
        d = _read(f, "cve_ent")
        if d is None:
            missing.append(f"Salud {y}: sin archivo (falta descargar o filtrar)")
        else:
            rows += _rows(pick(d, "cve_ent"), "cve_ent", None, y, "Salud", "DGIS Lesiones", DGIS, f)

    f = f"data/interim/endireh/endireh_{ENDIREH_EDITION}_estimates.csv"
    e = _read(f, "cve_ent")
    if e is None:
        missing.append("Encuesta: sin archivo")
    else:
        e = e[e["cve_ent"] != "00"]
        if state:
            e = e[e["cve_ent"] == state]
        for ind, rel, desc in ENDIREH:
            for _, r in e[e["indicator"] == ind].iterrows():
                base = {"cve_ent": r["cve_ent"], "nom_ent": common.STATES[r["cve_ent"]],
                        "anio": ENDIREH_EDITION, "sector": "Encuesta", "fuente": "ENDIREH 2021",
                        "indicador": ind, "descripcion": desc, "grupo_edad": AGE[r["age_group"]],
                        "relacion_agresor": rel, "archivo_origen": f}
                low = "sí" if r["n_num"] < LOW_N or bool(r["low_precision"]) else ""
                rows.append({**base, "unidad": "mujeres entrevistadas", "valor": r["n_num"],
                             "precision_baja": low})
                rows.append({**base, "unidad": "mujeres (estimación)", "valor": round(r["women"]),
                             "precision_baja": low})
    t = pd.DataFrame(rows)
    t["valor"] = pd.to_numeric(t["valor"]).round().astype("Int64")   # counts; empty = not reported
    order = {"Policía y fiscalías": 0, "Centros de Justicia para las Mujeres": 1, "Salud": 2, "Encuesta": 3}
    t = t.sort_values(["cve_ent", "sector", "anio"], key=lambda s: s.map(order) if s.name == "sector" else s,
                      kind="stable").reset_index(drop=True)
    return t, missing


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Step 4: one table, state x year x age group")
    p.add_argument("--years", type=int, nargs="+", default=[2024])
    p.add_argument("--state", help="two-digit INEGI state key, e.g. 09 for Ciudad de México")
    args = p.parse_args(argv)
    if args.state and args.state.zfill(2) not in common.STATES:
        raise SystemExit(f"Unknown state key {args.state}")
    state = args.state.zfill(2) if args.state else None

    t, missing = build(args.years, state)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    name = f"tabla_armonizada_{'_'.join(map(str, args.years))}" + (f"_{state}" if state else "")
    path = OUT_DIR / f"{name}.csv"
    t.to_csv(path, index=False, encoding="utf-8-sig")   # utf-8-sig so Excel shows accents

    print(f"{len(t)} filas, {t['cve_ent'].nunique()} estado(s), años {sorted(t['anio'].unique())}")
    for m in missing:
        print(f"  falta: {m}")
    print(f"Escrito {path.relative_to(common.core.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
