"""Tests for Step 2 CJM extraction, on a synthetic database with the real codebook layout."""

import pandas as pd
import pytest

from src.filter import cjm


@pytest.fixture
def colmap():
    return cjm.load_colmap()


def fake_bd(colmap):
    cols = {c: ["0", "0", "0"] for c in colmap}
    df = pd.DataFrame(cols)
    df.insert(0, "ID_CJM", ["09001_01", "09002_01", "14001_01"])
    df.insert(1, "NOM_CJM", ["A", "B", "C"])
    df.insert(2, "CVE_ENT", ["9", "09", "14"])
    df.insert(3, "NOM_ENT", ["CIUDAD DE MÉXICO", "CIUDAD DE MÉXICO", "JALISCO"])
    # 2024 (suffix _5 / _2): centre A
    df.loc[0, "P5_1_1_1_2"] = "100"
    df.loc[0, "P5_1_9_5_5"] = "10"     # 12-14  (excluded from 15+)
    df.loc[0, "P5_1_9_6_5"] = "20"     # 15-17  (in 15+, not 18+)
    df.loc[0, "P5_1_9_8_5"] = "70"     # 20-24
    df.loc[0, "P5_1_14_1_5"] = "200"   # all incidents
    df.loc[0, "P5_1_14_2_5"] = "80"    # pareja
    df.loc[0, "P5_1_14_3_5"] = "20"    # expareja
    df.loc[0, "P5_2_1_1_2"] = "30"
    # centre B: age data not available
    df.loc[1, "P5_1_9_8_5"] = "ND"
    df.loc[1, "P5_1_14_1_5"] = "50"
    df.loc[1, "P5_1_14_4_5"] = "25"    # novio
    # 2023 value that must be ignored for 2024
    df.loc[0, "P5_1_9_8_1"] = "999"
    return df


def test_spec_matches_codebook(colmap):
    spec = cjm.build_spec(2024, colmap)
    assert spec["women_15plus"][0] == "P5_1_9_6_5" and len(spec["women_15plus"]) == 11
    assert len(spec["women_18plus"]) == 10
    assert spec["incidents_partner"] == ["P5_1_14_2_5", "P5_1_14_3_5", "P5_1_14_4_5", "P5_1_14_5_5"]
    assert cjm.build_spec(2023, colmap)["women_total"] == ["P5_1_1_1_1"]
    with pytest.raises(SystemExit):
        cjm.build_spec(2025, colmap)


def test_extract_and_states(colmap):
    bd = fake_bd(colmap)
    # reporting (q5.2.1, 2024 = suffix _2): total includes non-reporters
    bd.loc[0, ["P5_2_1_1_2", "P5_2_1_2_2", "P5_2_1_3_2", "P5_2_1_4_2"]] = ["100", "25", "5", "70"]
    # centre C: every age column for 2024 not available -> women_15plus missing
    for g in cjm.AGE_15PLUS:
        bd.loc[2, f"P5_1_9_{g}_5"] = "ND"
    bd.loc[2, "P5_1_14_1_5"] = "ND"                     # total incidents unknown
    bd.loc[2, "P5_1_14_2_5"] = "40"                     # but partner incidents known
    c = cjm.extract(bd, cjm.build_spec(2024, colmap))
    a, b, cc = c.iloc[0], c.iloc[1], c.iloc[2]

    assert a["women_15plus"] == 90 and a["women_18plus"] == 70
    assert a["incidents_partner"] == 100 and a["share_partner_incidents"] == 0.5
    assert a["est_women_15plus_partner"] == 45
    assert a["women_reported"] == 30 and a["women_not_reported"] == 70   # not the 100 total

    # partial: one age group ND -> sum of the rest, flagged
    assert b["women_15plus"] == 0 and b["women_15plus_n_missing"] == 1
    assert b["incidents_partner"] == 25

    # all components ND -> missing, not 0
    assert pd.isna(cc["women_15plus"]) and cc["women_15plus_n_missing"] == 11

    s = cjm.to_states(c).set_index("CVE_ENT")
    assert s.loc["09", "n_centres"] == 2
    assert s.loc["09", "incidents_partner"] == 125 and s.loc["09", "incidents_total"] == 250
    # Jalisco: partner known (40) but total unknown -> no share, not a misleading ratio
    assert pd.isna(s.loc["14", "share_partner_incidents"])

    share, n = cjm.national_share(c)
    assert n == 2 and share == 125 / 250                  # centre C excluded from the ratio


def test_known_relationship_share_and_age_adjustment(colmap):
    bd = fake_bd(colmap)
    bd.loc[0, "P5_1_14_27_5"] = "100"     # 100 of 200 incidents: relationship not recorded
    bd.loc[0, "P5_1_9_1_5"] = "200"       # women by age: total 200 ...
    bd.loc[0, "P5_1_9_17_5"] = "100"      # ... 100 with unknown age
    c = cjm.extract(bd, cjm.build_spec(2024, colmap))
    a = c.iloc[0]
    assert a["share_partner_known_rel"] == 1.0          # 100 partner / (200 - 100)
    assert a["women_15plus_adj"] == 180                 # 90 x 200/100
    share_k, _ = cjm.national_share(c, known_rel=True)
    assert share_k == 125 / 150
