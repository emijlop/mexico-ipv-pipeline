"""Offline tests for Step 1: a local HTTP server stands in for the government sites."""

import csv
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest
import yaml

from src.acquire import core
from src.acquire.__main__ import main


@pytest.fixture
def site(tmp_path):
    root = tmp_path / "www"
    (root / "files").mkdir(parents=True)
    (root / "files" / "Lesiones_2024.zip").write_bytes(b"PK\x03\x04 fake zip v1")
    (root / "files" / "victimas_2015_2025.csv").write_bytes("Año,Sexo\n2025,Mujer\n".encode("latin-1"))
    (root / "files" / "victimas_nueva.csv").write_bytes("Año,Sexo\n2026,Mujer\n".encode())
    (root / "files" / "broken.zip").write_text("<!DOCTYPE html><html>Not found</html>")
    (root / "landing.html").write_text("""
      <a href="files/victimas_2015_2025.csv">Cifras de Víctimas del Fuero Común, 2015 - 2025</a>
      <a href="files/victimas_nueva.csv">Víctimas (nueva metodología 2026)</a>
      <a href="files/x.csv">Diccionario de víctimas</a>""", encoding="utf-8")
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *a: None
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}", root
    srv.shutdown()


@pytest.fixture
def repo(tmp_path, monkeypatch, site):
    base, _ = site
    r = tmp_path / "repo"
    (r / "config").mkdir(parents=True)
    cfg = {"sources": {
        "dgis": {"datasets": {"lesiones": {
            "years": [2010, 2030],
            "urls": [f"{base}/files/missing_{{year}}.zip", f"{base}/files/Lesiones_{{year}}.zip"]}}},
        "sesnsp": {"landing": f"{base}/landing.html", "datasets": {
            "victimas_old": {"years": [2015, 2025], "methodology": "CNSP/38/15",
                             "discover": {"link_regex": "(?i)v[ií]ctimas",
                                          "exclude_regex": "(?i)(nueva|diccionario)"}},
            "victimas_new": {"years": [2026, 2030],
                             "discover": {"link_regex": "(?i)v[ií]ctimas.*nueva"}},
            "html_trap": {"years": [2025, 2025], "urls": [f"{base}/files/broken.zip"]},
            "informe": {"years": [2015, 2030], "manual": True, "where": "Dic {yy} issue"}}},
        "cjm": {"edition_for_year": {2024: 2025}, "datasets": {"tab": {
            "years": [2021, 2024], "urls": [f"{base}/files/cjm{{edition}}.zip"]}}},
    }}
    (r / "config" / "sources.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True))
    monkeypatch.setattr(core, "ROOT", r)
    monkeypatch.setattr(core, "CONFIG_PATH", r / "config" / "sources.yaml")
    monkeypatch.setattr(core, "RAW_DIR", r / "data" / "raw")
    monkeypatch.setattr(core, "MANIFEST_PATH", r / "data" / "raw" / "manifest.csv")
    return r


def rows(repo):
    with open(repo / "data/raw/manifest.csv", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def ds(source, key):
    return next(d for d in core.iter_datasets(core.load_config(), source) if d.key == key)


def test_direct_url_fallback_and_manifest(repo):
    r = core.acquire(ds("dgis", "lesiones"), 2024, core.Manifest())
    assert r.status == "downloaded"
    assert r.path == repo / "data/raw/dgis/2024/lesiones/Lesiones_2024.zip"
    row = rows(repo)[0]
    assert row["url"].endswith("Lesiones_2024.zip") and len(row["sha256"]) == 64
    assert row["status"] == "current" and row["retrieved_at"]
    assert not (r.path.parent / ".incoming").exists()


def test_idempotent_skip_then_force_unchanged(repo):
    core.acquire(ds("dgis", "lesiones"), 2024, core.Manifest())
    assert core.acquire(ds("dgis", "lesiones"), 2024, core.Manifest()).status == "skipped"
    assert core.acquire(ds("dgis", "lesiones"), 2024, core.Manifest(), force=True).status == "unchanged"
    assert len(rows(repo)) == 1


def test_force_with_new_content_supersedes(repo, site):
    _, www = site
    core.acquire(ds("dgis", "lesiones"), 2024, core.Manifest())
    (www / "files" / "Lesiones_2024.zip").write_bytes(b"PK\x03\x04 fake zip v2 (revised)")
    r = core.acquire(ds("dgis", "lesiones"), 2024, core.Manifest(), force=True)
    assert r.status == "downloaded"
    m = rows(repo)
    assert [x["status"] for x in m] == ["superseded", "current"]
    old = repo / m[0]["file"]
    assert "_superseded" in m[0]["file"] and old.read_bytes().endswith(b"v1")
    assert r.path.read_bytes().endswith(b"(revised)")


def test_discovery_picks_right_link_and_logs_text(repo):
    r = core.acquire(ds("sesnsp", "victimas_old"), 2025, core.Manifest())
    assert r.status == "downloaded" and r.path.name == "victimas_2015_2025.csv"
    row = rows(repo)[0]
    assert "2015 - 2025" in row["link_text"] and row["methodology"] == "CNSP/38/15"
    r2 = core.acquire(ds("sesnsp", "victimas_new"), 2026, core.Manifest())
    assert r2.path.name == "victimas_nueva.csv"


def test_year_outside_range_and_missing_edition(repo):
    assert core.acquire(ds("sesnsp", "victimas_old"), 2026, core.Manifest()).status == "not_covered"
    assert core.acquire(ds("cjm", "tab"), 2025, core.Manifest()).status == "not_covered"


def test_edition_mapping_fills_url(repo):
    d = ds("cjm", "tab")
    assert d.fill(d.spec["urls"][0], 2024).endswith("/cjm2025.zip")


def test_html_error_page_is_rejected(repo):
    r = core.acquire(ds("sesnsp", "html_trap"), 2025, core.Manifest())
    assert r.status == "failed" and "HTML page" in r.message
    assert not (repo / "data/raw/manifest.csv").exists()


def test_manual_dataset_and_register(repo, tmp_path):
    r = core.acquire(ds("sesnsp", "informe"), 2025, core.Manifest())
    assert r.status == "manual" and "Dic 25" in r.message
    f = tmp_path / "Info-delict-violencia_contra_las_mujeres_Dic25.pdf"
    f.write_bytes(b"%PDF-1.4 fake")
    rr = core.register(ds("sesnsp", "informe"), 2025, f, core.Manifest(), notes="downloaded by hand")
    assert rr.status == "registered" and f.exists()  # original untouched
    row = rows(repo)[0]
    assert row["method"] == "manual" and row["notes"] == "downloaded by hand"


def test_gdrive_link_conversion():
    u = "https://drive.google.com/file/d/1AbC-xyz_9/view?usp=sharing"
    assert core.gdrive_direct(u) == ("https://drive.usercontent.google.com/download?"
                                     "id=1AbC-xyz_9&export=download&confirm=t")
    assert core.gdrive_direct("https://x.org/a.zip") == "https://x.org/a.zip"


def test_cli_run_and_status(repo, capsys):
    code = main(["run", "--year", "2024", "--source", "dgis"])
    assert code == 0
    main(["status", "--year", "2024", "--source", "dgis"])
    out = capsys.readouterr().out
    assert "✓ dgis/lesiones [2024] downloaded" in out and "OK" in out


def test_edition_sources_stored_once(repo, site):
    _, www = site
    (www / "files" / "cjm2025.zip").write_bytes(b"PK\x03\x04 cjm")
    cfg = core.load_config()
    cfg["sources"]["cjm"]["edition_for_year"][2023] = 2025
    cfg["sources"]["cjm"]["datasets"]["tab"]["years"] = [2021, 2024]
    (repo / "config/sources.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True))
    r1 = core.acquire(ds("cjm", "tab"), 2024, core.Manifest())
    r2 = core.acquire(ds("cjm", "tab"), 2023, core.Manifest())
    assert r1.status == "downloaded" and r2.status == "skipped"
    assert r1.path == repo / "data/raw/cjm/ed2025/tab/cjm2025.zip"
    assert rows(repo)[0]["year"] == "ed2025" and rows(repo)[0]["edition"] == "2025"


def test_sharepoint_link_conversion():
    u = "https://sspcgob-my.sharepoint.com/:u:/g/personal/cni_sspc_gob_mx/IQC7gjMD?e=cNhRp0"
    assert core.gdrive_direct(u) == u + "&download=1"
    assert core.gdrive_direct(u + "&download=1") == u + "&download=1"
    x = "https://sspcgob-my.sharepoint.com/:x:/g/personal/cni_sspc_gob_mx/Eft_H"
    assert core.gdrive_direct(x) == x + "?download=1"


def test_multi_year_file_stored_once(repo):
    cfg = core.load_config()
    cfg["sources"]["sesnsp"]["datasets"]["victimas_old"]["multi_year_file"] = True
    (repo / "config/sources.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True))
    r1 = core.acquire(ds("sesnsp", "victimas_old"), 2024, core.Manifest())
    r2 = core.acquire(ds("sesnsp", "victimas_old"), 2025, core.Manifest())
    assert r1.status == "downloaded" and r2.status == "skipped"
    assert r1.path == repo / "data/raw/sesnsp/2015-2025/victimas_old/victimas_2015_2025.csv"


class FakeResp:
    def __init__(self, cd="", ctype=""):
        self.headers = {"Content-Disposition": cd, "Content-Type": ctype}


def test_filename_rfc5987_and_extension():
    f = core.filename_from_response
    sp = "https://x.sharepoint.com/:u:/g/personal/a/IQC7?e=1&download=1"
    assert f(FakeResp("attachment; filename*=utf-8''Estatal-V%C3%ADctimas-2015-2025_sep2026.zip"), sp) \
        == "Estatal-Víctimas-2015-2025_sep2026.zip"
    assert f(FakeResp('attachment; filename="a.csv"; filename*=UTF-8\'\'b%20c.csv'), sp) == "b c.csv"
    assert f(FakeResp('attachment; filename="plain.pdf"'), sp) == "plain.pdf"
    xl = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert f(FakeResp("", xl), "https://x.sharepoint.com/:x:/g/personal/a/Eft_H?e=x") == "Eft_H.xlsx"


def test_force_renames_badly_named_file(repo):
    d = ds("dgis", "lesiones")
    r = core.acquire(d, 2024, core.Manifest())
    bad = r.path.with_name("utf-8''Lesiones_2024.zip")
    r.path.rename(bad)
    m = core.Manifest()
    m.rows[0]["file"] = str(bad.relative_to(repo))
    m.save()
    r2 = core.acquire(d, 2024, core.Manifest(), force=True)
    assert r2.status == "unchanged" and r2.path.name == "Lesiones_2024.zip" and r2.path.exists()
    assert not bad.exists() and rows(repo)[0]["file"].endswith("/Lesiones_2024.zip")
    assert "renamed from" in rows(repo)[0]["notes"]
