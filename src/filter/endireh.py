"""Step 2 - ENDIREH: partner-violence prevalence and help-seeking, women 15+ / 18+.

Input : conjunto_de_datos_endireh_<edition>_csv.zip, via the manifest. Tables used:
        TB_VD (violence flags, weights, design), TSDem (age), TB_SEC_XIV and XIV_2
        (help-seeking for violence in the current or last relationship).
Output: data/interim/endireh/endireh_<edition>_estimates.csv  (long format:
        state x age group x indicator, with survey-weighted estimates, SE and 95% CI)

Definitions (codes checked against the 2021 catalogues; see docs/ipv_crosswalk.csv):
- ipv_12m  = VPAR_12M == 1 (any partner violence in the last 12 months, current or
  last relationship). 1 = yes, 2 = no, 9 = not specified; blank = never had a partner.
  With women who ever had a partner as denominator this reproduces INEGI's 20.7%.
- ipv_life = VPAR_A == 1 (any partner violence over the current or last relationship).
- Help-seeking was asked of women with ipv_life (P14_7 ... P14_15). It refers to the
  whole relationship, not to the last 12 months. 'Recent' versions use the year of the
  last request/complaint (2020 or 2021), a proxy for the reference period.
- 9 ('no especificado') counts as 'not yes' and stays in the denominator.
- Standard errors: Taylor linearisation, strata EST_DIS, PSUs UPM_DIS, weight FAC_MUJ.

Usage:  python -m src.filter.endireh --edition 2021
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from src.filter import common

OUT_DIR = common.INTERIM / "endireh"
Z95 = 1.959964
RECENT_YEARS = {"2020", "2021"}

# variable -> (table, meaning). Institution numbers follow the questionnaire (P14_8_x, P14_14_x).
HELP_VARS = {
    "P14_7_1": ("TB_SEC_XIV", "asked an institution for support, information or services"),
    "P14_7_2": ("TB_SEC_XIV", "filed a complaint or report with an authority"),
    "P14_8_5": ("TB_SEC_XIV", "asked a Centro de Justicia para las Mujeres"),
    "P14_8_7": ("TB_SEC_XIV", "asked a public clinic, health centre or hospital"),
    "P14_10_5": ("TB_SEC_XIV", "year of last request to a CJM"),
    "P14_10_7": ("TB_SEC_XIV", "year of last request to public health"),
    "P14_14_1": ("TB_SEC_XIV_2", "complaint to the police"),
    "P14_14_4": ("TB_SEC_XIV_2", "complaint to the Ministerio Público"),
    "P14_15_1": ("TB_SEC_XIV_2", "year of last complaint to the police"),
    "P14_15_4": ("TB_SEC_XIV_2", "year of last complaint to the Ministerio Público"),
}

# indicator -> (numerator column, denominator column)
INDICATORS = {
    "ipv_12m":                    ("ipv_12m", "all"),
    "ipv_12m_ever_partnered":     ("ipv_12m", "ever_partnered"),
    "ipv_life_ever_partnered":    ("ipv_life", "ever_partnered"),
    # help-seeking among women with partner violence in the relationship
    "sought_institution":         ("sought_institution", "ipv_life"),
    "complaint_authority":        ("complaint_authority", "ipv_life"),
    "sought_or_complaint":        ("sought_or_complaint", "ipv_life"),
    "sought_cjm":                 ("sought_cjm", "ipv_life"),
    "sought_health_public":       ("sought_health_public", "ipv_life"),
    "complaint_police":           ("complaint_police", "ipv_life"),
    "complaint_mp":               ("complaint_mp", "ipv_life"),
    "complaint_police_or_mp":     ("complaint_police_or_mp", "ipv_life"),
    # same, among women with partner violence in the last 12 months
    "ipv12m_sought_or_complaint": ("sought_or_complaint", "ipv_12m"),
    "ipv12m_sought_cjm":          ("sought_cjm", "ipv_12m"),
    "ipv12m_sought_health_public": ("sought_health_public", "ipv_12m"),
    "ipv12m_complaint_police_or_mp": ("complaint_police_or_mp", "ipv_12m"),
    # last contact in 2020-2021 (reference-period proxy), among ipv_12m
    "ipv12m_recent_cjm":          ("recent_cjm", "ipv_12m"),
    "ipv12m_recent_health_public": ("recent_health_public", "ipv_12m"),
    "ipv12m_recent_police_or_mp": ("recent_police_or_mp", "ipv_12m"),
}
AGE_GROUPS = {"15plus": (15, None), "18plus": (18, None), "15to17": (15, 17)}   # (min, max) age


def _table(zip_path, table: str, cols: list[str]) -> pd.DataFrame:
    df = common.read_zip_csv(zip_path, f"conjunto_de_datos_{table}.csv", dtype=str,
                             encoding="latin-1", usecols=lambda c: c.strip() in cols)
    df.columns = [c.strip() for c in df.columns]
    return df.apply(lambda s: s.str.strip())   # last column carries a stray '\r'


def load(edition: int) -> pd.DataFrame:
    path = common.raw_file("endireh", "microdatos_csv", f"ed{edition}")
    vd = _table(path, "TB_VD", ["ID_PER", "CVE_ENT", "POBP", "VPAR_A", "VPAR_12M",
                                "FAC_MUJ", "EST_DIS", "UPM_DIS"])
    age = _table(path, "TSDem", ["ID_PER", "EDAD"])
    df = vd.merge(age, on="ID_PER", how="left", validate="1:1")
    for table in sorted({t for t, _ in HELP_VARS.values()}):
        cols = [v for v, (t, _) in HELP_VARS.items() if t == table]
        df = df.merge(_table(path, table, ["ID_PER", *cols]), on="ID_PER", how="left",
                      validate="1:1")
    if df["EDAD"].isna().any():
        raise SystemExit(f"{df['EDAD'].isna().sum()} women have no age in TSDem")
    return df


def flags(df: pd.DataFrame) -> pd.DataFrame:
    yes = lambda v: (df[v] == "1").astype(float)
    f = pd.DataFrame({
        "cve_ent": df["CVE_ENT"].str.zfill(2),
        "edad": pd.to_numeric(df["EDAD"]),
        "w": pd.to_numeric(df["FAC_MUJ"]),
        "strata": df["EST_DIS"], "psu": df["EST_DIS"] + "_" + df["UPM_DIS"],
        "all": 1.0,
        "ever_partnered": yes("POBP"),
        "ipv_12m": yes("VPAR_12M"),
        "ipv_life": yes("VPAR_A"),
        "sought_institution": yes("P14_7_1"),
        "complaint_authority": yes("P14_7_2"),
        "sought_cjm": yes("P14_8_5"),
        "sought_health_public": yes("P14_8_7"),
        "complaint_police": yes("P14_14_1"),
        "complaint_mp": yes("P14_14_4"),
        "recent_cjm": df["P14_10_5"].isin(RECENT_YEARS).astype(float),
        "recent_health_public": df["P14_10_7"].isin(RECENT_YEARS).astype(float),
    })
    f["sought_or_complaint"] = f[["sought_institution", "complaint_authority"]].max(axis=1)
    f["complaint_police_or_mp"] = f[["complaint_police", "complaint_mp"]].max(axis=1)
    f["recent_police_or_mp"] = (df["P14_15_1"].isin(RECENT_YEARS)
                                | df["P14_15_4"].isin(RECENT_YEARS)).astype(float)
    # help-seeking can only be 'yes' for women asked the module
    bad = (f["sought_or_complaint"] > f["ipv_life"]).sum()
    if bad:
        raise SystemExit(f"{bad} women report help-seeking without ipv_life - check codes")
    return f


def _design(f: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Integer codes for PSUs and their strata (computed once per frame, then reused)."""
    if "_psu_code" not in f:
        f["_psu_code"], psus = pd.factorize(f["psu"])
        h_of_psu = pd.Series(f["strata"].values).groupby(f["_psu_code"].values).first()
        f.attrs["h_of_psu"] = pd.factorize(h_of_psu.sort_index().values)[0]
    h = f.attrs["h_of_psu"]
    return f["_psu_code"].values, h, np.bincount(h)


def _design_var(u: np.ndarray, psu: np.ndarray, h_of_psu: np.ndarray, n_h: np.ndarray) -> float:
    """Variance of a total of linearised values u (with-replacement PSU approximation)."""
    t = np.bincount(psu, weights=u, minlength=len(h_of_psu))          # PSU totals
    mean_h = np.bincount(h_of_psu, weights=t, minlength=len(n_h)) / n_h
    ss = np.bincount(h_of_psu, weights=(t - mean_h[h_of_psu]) ** 2, minlength=len(n_h))
    keep = n_h > 1                                                      # singleton strata add nothing
    return float((n_h[keep] / (n_h[keep] - 1) * ss[keep]).sum())


def estimate(f: pd.DataFrame, domain: pd.Series, num: str, den: str) -> dict:
    d = domain.astype(float).values
    w, x = f["w"].values, f[den].values
    y = f[num].values * x                      # numerator is always within the denominator
    Y, X = (w * d * y).sum(), (w * d * x).sum()
    n_den = int((d * x).sum())
    if X == 0:
        return {"estimate": np.nan, "se": np.nan, "women": Y, "women_se": np.nan,
                "n_num": 0, "n_den": n_den}
    R = Y / X
    design = _design(f)
    se_r = np.sqrt(_design_var(w * d * (y - R * x) / X, *design))
    se_y = np.sqrt(_design_var(w * d * y, *design))
    return {"estimate": R, "se": se_r, "women": Y, "women_se": se_y,
            "n_num": int((d * y).sum()), "n_den": n_den}


def build(f: pd.DataFrame) -> pd.DataFrame:
    rows = []
    areas = [("00", "Nacional", pd.Series(True, index=f.index))]
    areas += [(k, v, f["cve_ent"] == k) for k, v in common.STATES.items()]
    for cve, nom, in_area in areas:
        for ag, (lo, hi) in AGE_GROUPS.items():
            domain = in_area & (f["edad"] >= lo)
            if hi is not None:
                domain &= f["edad"] <= hi
            pop = estimate(f, domain, "all", "all")
            for ind, (num, den) in INDICATORS.items():
                r = estimate(f, domain, num, den)
                rows.append({"cve_ent": cve, "nom_ent": nom, "age_group": ag, "indicator": ind,
                             "numerator": num, "denominator": den, **r,
                             "women_in_age_group": pop["women"]})
    out = pd.DataFrame(rows)
    out["ci_low"] = (out["estimate"] - Z95 * out["se"]).clip(lower=0)
    out["ci_high"] = (out["estimate"] + Z95 * out["se"]).clip(upper=1)
    out["cv"] = out["se"] / out["estimate"]
    # INEGI convention: CV > 30% = low precision; flag small samples too
    out["low_precision"] = (out["cv"] > 0.30) | (out["n_num"] < 30)
    cols = ["cve_ent", "nom_ent", "age_group", "indicator", "numerator", "denominator",
            "estimate", "se", "ci_low", "ci_high", "cv", "women", "women_se",
            "women_in_age_group", "n_num", "n_den", "low_precision"]
    return out[cols]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Step 2: ENDIREH partner violence and help-seeking")
    p.add_argument("--edition", type=int, default=2021)
    args = p.parse_args(argv)

    f = flags(load(args.edition))
    if f["edad"].min() < 15:
        raise SystemExit("ENDIREH should only contain women 15+")
    est = build(f)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"endireh_{args.edition}_estimates.csv"
    est.to_csv(path, index=False)

    nat = est[(est["cve_ent"] == "00") & (est["age_group"] == "15plus")].set_index("indicator")
    print(f"ENDIREH {args.edition}: {len(f):,} women interviewed, "
          f"{nat.loc['ipv_12m', 'women_in_age_group']:,.0f} women 15+ (weighted)")
    for ind in INDICATORS:
        r = nat.loc[ind]
        print(f"  {ind:32} {r['estimate']:6.1%}  [{r['ci_low']:.1%}-{r['ci_high']:.1%}]  "
              f"= {r['women']:>11,.0f} women  (n={r['n_num']:,})")
    n_low = est.loc[est["cve_ent"] != "00", "low_precision"].mean()
    print(f"  state-level estimates flagged low precision: {n_low:.0%}")
    print(f"\nWrote {path.relative_to(common.core.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
