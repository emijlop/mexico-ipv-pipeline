"""Offline tests for the Step 2 SESNSP, DGIS and ENDIREH filters, on small synthetic data."""

import zipfile

import numpy as np
import pandas as pd
import pytest

from src.filter import common, dgis, endireh, sesnsp

MONTHS = sesnsp.MONTHS


# ------------------------------------------------------------------ SESNSP

def _sesnsp_zip(tmp_path, name, rows, cols):
    df = pd.DataFrame(rows, columns=cols + MONTHS)
    p = tmp_path / f"{name}.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr(f"{name}.csv", df.to_csv(index=False).encode("latin-1"))
    return p


@pytest.fixture
def sesnsp_raw(tmp_path, monkeypatch):
    base = ["Año", "Clave_Ent", "Entidad", "Bien jurídico afectado", "Tipo de delito",
            "Subtipo de delito", "Modalidad"]
    one = [1] * 12
    carpetas = [
        [2024, 9, "CDMX", "La familia", "Violencia familiar", "Violencia familiar", "x", *[10] * 12],
        [2024, 9, "CDMX", "La familia",
         "Violencia de género en todas sus modalidades distinta a la violencia familiar", "x", "x", *one],
        [2024, 9, "CDMX", "v", "Feminicidio", "Feminicidio", "Con arma blanca", *one],
        [2024, 9, "CDMX", "v", "Feminicidio", "Feminicidio", "No especificado", *one],
        [2024, 9, "CDMX", "s", "Violación simple", "Violación simple", "x", *one],
        [2024, 9, "CDMX", "s", "Violación equiparada", "Violación equiparada", "x", *one],
        [2024, 9, "CDMX", "s", "Abuso sexual", "Abuso sexual", "x", *one],
        [2024, 9, "CDMX", "s", "Acoso sexual", "Acoso sexual", "x", *one],
        [2024, 9, "CDMX", "v", "Lesiones", "Lesiones dolosas", "Con arma blanca", *one],
        [2024, 9, "CDMX", "v", "Lesiones", "Lesiones culposas", "x", *[99] * 12],   # excluded
        # Jalisco: December not yet published
        [2024, 14, "Jal", "La familia", "Violencia familiar", "Violencia familiar", "x", *[5] * 11, None],
    ]
    vbase = base + ["Sexo", "Rango de edad"]
    victimas = [
        [2024, 9, "CDMX", "v", "Feminicidio", "Feminicidio", "x", "Mujer", "Adultos (18 y más)", *one],
        [2024, 9, "CDMX", "v", "Feminicidio", "Feminicidio", "x", "Mujer", "Menores de edad (0-17)", *one],
        [2024, 9, "CDMX", "v", "Feminicidio", "Feminicidio", "x", "Mujer", "No especificado", *one],
        [2024, 9, "CDMX", "v", "Homicidio", "Homicidio doloso", "x", "Mujer", "Adultos (18 y más)", *one],
        [2024, 9, "CDMX", "v", "Homicidio", "Homicidio doloso", "x", "Hombre", "Adultos (18 y más)", *[50] * 12],
        [2024, 9, "CDMX", "v", "Lesiones", "Lesiones dolosas", "x", "Mujer", "Adultos (18 y más)", *[2] * 12],
    ]
    files = {"carpetas_estatal_2015_2025": _sesnsp_zip(tmp_path, "c", carpetas, base),
             "victimas_2015_2025": _sesnsp_zip(tmp_path, "v", victimas, vbase)}
    monkeypatch.setattr(common, "raw_file", lambda src, ds, key: files[ds])


def test_sesnsp_categories_and_victims(sesnsp_raw):
    t = sesnsp.build().set_index("cve_ent")
    cdmx, jal = t.loc["09"], t.loc["14"]
    assert cdmx["carpetas_violencia_familiar"] == 120
    assert cdmx["carpetas_feminicidio"] == 24            # both modalities
    assert cdmx["carpetas_violacion"] == 24              # simple + equiparada
    assert cdmx["carpetas_lesiones_dolosas"] == 12       # culposas excluded
    assert cdmx["women_18plus_feminicidio"] == 12
    assert cdmx["women_minors_feminicidio"] == 12
    assert cdmx["women_age_unknown_feminicidio"] == 12
    assert cdmx["women_18plus_homicidio_doloso"] == 12   # men excluded
    assert cdmx["nom_ent"] == "Ciudad de México"
    assert jal["carpetas_violencia_familiar"] == 55 and jal["carpetas_months_reported"] == 11


def test_sesnsp_rejects_new_methodology_years(sesnsp_raw):
    with pytest.raises(SystemExit):
        sesnsp.main(["--year", "2026"])


def test_sesnsp_fails_loudly_on_renamed_category():
    df = pd.DataFrame({"Tipo de delito": ["Otro"], "Subtipo de delito": ["Otro"]})
    with pytest.raises(SystemExit, match="renamed"):
        sesnsp.select(df, {"violencia_familiar": ("Tipo de delito", ["Violencia familiar"])}, "x")


# ------------------------------------------------------------------ DGIS

def test_dgis_partner_women_15plus():
    codes = dgis.load_codes()
    ev = pd.DataFrame([
        # ID, Clues, CVEEDAD, Edad, SEXO, CodEstado, Intenc., Parentesco, CodMP, Anio
        ["1", "DFSSA000001", "5", "30", "2", "09", "2", "3", "1", "2024"],   # partner, 15+, 18+, MP
        ["2", "DFSSA000001", "5", "16", "2", "09", "2", "3", "2", "2024"],   # partner, 15+ not 18+
        ["3", "DFSSA000002", "5", "14", "2", "09", "2", "3", "2", "2024"],   # under 15
        ["4", "DFSSA000001", "5", "40", "1", "09", "2", "3", "2", "2024"],   # man
        ["5", "DFSSA000001", "5", "40", "2", "09", "2", "1", "2", "2024"],   # father, not partner
        ["6", "DFSSA000001", "5", "40", "2", "09", "2", "-1", "2", "2024"],  # relationship unknown
        ["7", "DFSSA000001", "9", "999", "2", "09", "2", "3", "2", "2024"],  # age unknown
        ["8", "JCIMB000001", "4", "6", "2", "14", "2", "3", "2", "2024"],    # 6 MONTHS old
        ["9", "JCIMB000001", "5", "50", "2", "14", "3", "7", "2", "2024"],   # non-family
        ["10", "JCIMB000001", "5", "50", "2", "14", "2", "3", "2", "2023"],  # other year
    ], columns=dgis.EVENT_COLS)
    tv = pd.DataFrame({"ID": ["1", "1", "2"], "CodTipoViolencia": ["6", "8", "7"]})
    s = dgis.to_states(dgis.flag(ev, tv, 2024, codes), codes).set_index("cve_ent")
    cdmx, jal = s.loc["09"], s.loc["14"]
    assert cdmx["women_15plus_partner"] == 2 and cdmx["women_18plus_partner"] == 1
    assert cdmx["women_age_unknown_partner"] == 1
    assert cdmx["women_15plus_violencia_familiar"] == 4          # 1, 2, 5, 6
    assert cdmx["women_15plus_vf_relationship_unknown"] == 1
    assert cdmx["share_partner_of_vf_known_rel_15plus"] == 2 / 3
    assert cdmx["women_15plus_partner_aviso_mp"] == 1
    assert cdmx["women_15plus_partner_fisica"] == 1 and cdmx["women_15plus_partner_sexual"] == 1
    assert jal["women_15plus_partner"] == 0                      # 6 months, not 6 years
    assert jal["women_under15_partner"] == 1                     # the 6-month-old counts as under 15
    assert cdmx["women_15_17_partner"] == 1 and cdmx["women_under15_partner"] == 1   # ages 16 and 14
    assert jal["women_15plus_violencia_no_familiar"] == 1
    assert pd.isna(s.loc["01", "records_all"])                   # state with no units stays missing
    assert len(s) == 32


def test_dgis_unknown_clues_prefix_fails():
    codes = dgis.load_codes()
    ev = pd.DataFrame([["1", "XXSSA000001", "5", "30", "2", "09", "2", "3", "1", "2024"]],
                      columns=dgis.EVENT_COLS)
    with pytest.raises(SystemExit, match="CLUES"):
        dgis.flag(ev, pd.DataFrame(columns=["ID", "CodTipoViolencia"]), 2024, codes)


# ------------------------------------------------------------------ ENDIREH

def _endireh_raw():
    blank = {v: "" for v in endireh.HELP_VARS}
    rows = [
        # partnered, violence 12m and lifetime, sought CJM in 2021, complaint to MP in 2019
        dict(ID_PER="a", CVE_ENT="9", POBP="1", VPAR_A="1", VPAR_12M="1", EDAD="30",
             **{**blank, "P14_7_1": "1", "P14_8_5": "1", "P14_10_5": "2021",
                "P14_7_2": "1", "P14_14_4": "1", "P14_15_4": "2019"}),
        # partnered, lifetime only, no help
        dict(ID_PER="b", CVE_ENT="9", POBP="1", VPAR_A="1", VPAR_12M="2", EDAD="16",
             **{**blank, "P14_7_1": "2", "P14_7_2": "9"}),
        # partnered, no violence
        dict(ID_PER="c", CVE_ENT="9", POBP="1", VPAR_A="2", VPAR_12M="2", EDAD="40", **blank),
        # never partnered (blank flags)
        dict(ID_PER="d", CVE_ENT="9", POBP="0", VPAR_A="", VPAR_12M="", EDAD="20", **blank),
    ]
    df = pd.DataFrame(rows)
    df["FAC_MUJ"] = ["100", "100", "200", "100"]
    df["EST_DIS"] = ["1", "1", "2", "2"]
    df["UPM_DIS"] = ["1", "2", "3", "4"]
    return df


def test_endireh_flags():
    f = endireh.flags(_endireh_raw())
    a, b, d = f.iloc[0], f.iloc[1], f.iloc[3]
    assert a["ipv_12m"] == 1 and a["sought_cjm"] == 1 and a["recent_cjm"] == 1
    assert a["complaint_police_or_mp"] == 1 and a["recent_police_or_mp"] == 0   # 2019
    assert b["ipv_12m"] == 0 and b["ipv_life"] == 1 and b["complaint_authority"] == 0  # 9 = not yes
    assert d["ever_partnered"] == 0 and d["ipv_12m"] == 0
    assert f["cve_ent"].iloc[0] == "09"


def test_endireh_weighted_estimates():
    f = endireh.flags(_endireh_raw())
    dom = pd.Series(True, index=f.index)
    r = endireh.estimate(f, dom, "ipv_12m", "all")
    assert r["estimate"] == pytest.approx(100 / 500) and r["women"] == 100
    r = endireh.estimate(f, dom, "ipv_12m", "ever_partnered")
    assert r["estimate"] == pytest.approx(100 / 400)
    r = endireh.estimate(f, dom, "sought_cjm", "ipv_life")
    assert r["estimate"] == pytest.approx(0.5) and r["n_den"] == 2 and r["n_num"] == 1
    r = endireh.estimate(f, f["edad"] >= 18, "ipv_life", "ever_partnered")   # woman b (16) out
    assert r["estimate"] == pytest.approx(100 / 300)
    # empty denominator -> missing, not zero
    r = endireh.estimate(f, pd.Series(False, index=f.index), "ipv_12m", "all")
    assert np.isnan(r["estimate"])


def test_endireh_linearised_se_matches_formula():
    # one stratum, 4 PSUs, equal weights, proportion p: SE = sqrt(n/(n-1) * sum((y-p)^2)) / n
    f = pd.DataFrame({"w": [1.0] * 4, "all": [1.0] * 4, "y": [1.0, 0, 0, 0],
                      "strata": ["1"] * 4, "psu": ["1", "2", "3", "4"]})
    r = endireh.estimate(f, pd.Series(True, index=f.index), "y", "all")
    expected = np.sqrt(4 / 3 * ((0.75 ** 2) + 3 * 0.25 ** 2)) / 4
    assert r["se"] == pytest.approx(expected)
