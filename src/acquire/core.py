"""Shared machinery for Step 1 (Acquire).

Responsibilities:
- load config/sources.yaml and resolve a dataset for a reference year
- download files idempotently (skip if already logged with the same hash)
- discover links on a landing page when direct URLs fail
- register manually obtained files (transparency responses, PDFs)
- keep data/raw/manifest.csv as the single provenance log

Raw files are never edited. If a re-download (--force) brings different
content, the previous file is moved to data/raw/_superseded/<date>/ and both
versions stay in the manifest.
"""

from __future__ import annotations

import csv
import hashlib
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "sources.yaml"
RAW_DIR = ROOT / "data" / "raw"
MANIFEST_PATH = RAW_DIR / "manifest.csv"

MANIFEST_FIELDS = [
    "source", "dataset", "year", "edition", "file", "url", "link_text",
    "retrieved_at", "sha256", "bytes", "methodology", "method", "status", "notes",
]

USER_AGENT = "mexico-ipv-pipeline/0.1 (academic research; data acquisition)"
TIMEOUT = 60


# --------------------------------------------------------------------- config

@dataclass
class Dataset:
    source: str
    key: str
    spec: dict
    source_spec: dict

    @property
    def years(self) -> tuple[int, int]:
        y = self.spec.get("years", [1900, 2100])
        return int(y[0]), int(y[1])

    def covers(self, year: int) -> bool:
        lo, hi = self.years
        return lo <= year <= hi

    def edition(self, year: int) -> int | None:
        """Edition that holds `year` (CJM, ENDIREH); None for year-based sources."""
        if "fixed_edition" in self.source_spec:
            return int(self.source_spec["fixed_edition"])
        mapping = self.source_spec.get("edition_for_year")
        if mapping:
            return mapping.get(year) or mapping.get(str(year))
        return None

    def fill(self, template: str, year: int) -> str:
        ed = self.edition(year)
        return template.format(year=year, yy=str(year)[-2:], edition=ed if ed else year)

    def slot(self, year: int) -> str:
        """Folder/manifest key. Edition-based sources are stored once per edition
        (e.g. 'ed2025') and multi-year files once per range (e.g. '2015-2025'),
        so asking for 2024 and then 2025 doesn't duplicate the file."""
        if self.spec.get("multi_year_file"):
            lo, hi = self.years
            return f"{lo}-{hi}"
        ed = self.edition(year)
        return f"ed{ed}" if ed else str(year)

    @property
    def manual(self) -> bool:
        return bool(self.spec.get("manual"))


def load_config(path: Path | None = None) -> dict:
    with open(path or CONFIG_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def iter_datasets(config: dict, source: str | None = None) -> Iterable[Dataset]:
    for s_key, s_spec in config["sources"].items():
        if source and s_key != source:
            continue
        for d_key, d_spec in s_spec.get("datasets", {}).items():
            yield Dataset(s_key, d_key, d_spec, s_spec)


# ------------------------------------------------------------------- manifest

class Manifest:
    def __init__(self, path: Path | None = None):
        path = path or MANIFEST_PATH
        self.path = path
        self.rows: list[dict] = []
        if path.exists():
            with open(path, newline="", encoding="utf-8") as fh:
                self.rows = list(csv.DictReader(fh))

    def latest(self, source: str, dataset: str, year: int | str) -> dict | None:
        hits = [r for r in self.rows
                if r["source"] == source and r["dataset"] == dataset
                and r["year"] == str(year) and r["status"] == "current"]
        return hits[-1] if hits else None

    def append(self, row: dict) -> None:
        for r in self.rows:  # older entries for the same slot become superseded
            if (r["source"], r["dataset"], r["year"], r["status"]) == (
                    row["source"], row["dataset"], str(row["year"]), "current"):
                r["status"] = "superseded"
        self.rows.append({k: row.get(k, "") for k in MANIFEST_FIELDS})
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
            w.writeheader()
            w.writerows(self.rows)
        tmp.replace(self.path)


# -------------------------------------------------------------------- helpers

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def gdrive_direct(url: str) -> str:
    """Turn a share link into a direct-download URL.

    - Google Drive share links -> drive.usercontent.google.com download URL
    - SharePoint/OneDrive share links (SESNSP since 2026, e.g.
      https://sspcgob-my.sharepoint.com/:u:/g/personal/.../ID?e=abc) -> same URL + download=1
    """
    m = re.search(r"drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)([\w-]+)", url)
    if m:
        return f"https://drive.usercontent.google.com/download?id={m.group(1)}&export=download&confirm=t"
    if re.search(r"\.sharepoint\.com/:[a-z]:/", url) or "1drv.ms" in url:
        if re.search(r"[?&]download=1", url):
            return url
        return url + ("&" if "?" in url else "?") + "download=1"
    return url


def session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    adapter = requests.adapters.HTTPAdapter(max_retries=requests.adapters.Retry(
        total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504]))
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


CONTENT_TYPE_EXT = {
    "spreadsheetml": ".xlsx", "ms-excel": ".xls", "zip": ".zip", "pdf": ".pdf",
    "text/csv": ".csv", "wordprocessingml": ".docx", "json": ".json",
}


def filename_from_response(resp: requests.Response, url: str) -> str:
    """Best file name: RFC 5987 filename* > filename= > URL path; add an extension if missing."""
    cd = resp.headers.get("Content-Disposition", "")
    name = ""
    m = re.search(r"filename\*\s*=\s*([\w-]+)''([^;]+)", cd, re.I)      # filename*=utf-8''Na%C3%ADme.zip
    if m:
        name = unquote(m.group(2).strip().strip('"'), encoding=m.group(1) or "utf-8")
    else:
        m = re.search(r'filename\s*=\s*"?([^";]+)"?', cd, re.I)
        if m:
            name = unquote(m.group(1).strip())
    if not name:
        name = unquote(urlparse(url).path.rstrip("/").split("/")[-1])
    name = Path(name).name or "download"
    if not Path(name).suffix:
        ctype = resp.headers.get("Content-Type", "").lower()
        ext = next((e for k, e in CONTENT_TYPE_EXT.items() if k in ctype), "")
        name += ext
    return name


def looks_like_html(path: Path) -> bool:
    with open(path, "rb") as fh:
        head = fh.read(512).lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


# ------------------------------------------------------------------ discovery

@dataclass
class Link:
    url: str
    text: str


def list_links(landing: str, sess: requests.Session | None = None) -> list[Link]:
    sess = sess or session()
    resp = sess.get(landing, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ", strip=True).split())
        links.append(Link(urljoin(landing, a["href"]), text))
    return links


def discover(ds: Dataset, year: int, sess: requests.Session | None = None) -> Link | None:
    disc = ds.spec.get("discover")
    landing = ds.spec.get("landing") or ds.source_spec.get("landing")
    if not disc or not landing:
        return None
    landing = ds.fill(landing, year)
    pattern = re.compile(ds.fill(disc["link_regex"], year))
    exclude = re.compile(ds.fill(disc["exclude_regex"], year)) if disc.get("exclude_regex") else None
    for link in list_links(landing, sess):
        hay = f"{link.text} {link.url}"
        if pattern.search(hay) and not (exclude and exclude.search(hay)):
            return link
    return None


# ------------------------------------------------------------------- download

@dataclass
class Result:
    dataset: Dataset
    year: int
    status: str            # downloaded | skipped | unchanged | manual | not_covered | failed
    path: Path | None = None
    url: str = ""
    message: str = ""
    tried: list[str] = field(default_factory=list)


def target_dir(ds: Dataset, year: int) -> Path:
    return RAW_DIR / ds.source / ds.slot(year) / ds.key


def fetch(url: str, dest_dir: Path, sess: requests.Session) -> Path:
    """Stream `url` into dest_dir/.partial, return final path. Raises on failure."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    real_url = gdrive_direct(url)
    with sess.get(real_url, stream=True, timeout=TIMEOUT) as resp:
        resp.raise_for_status()
        name = filename_from_response(resp, real_url)
        tmp = dest_dir / f".{name}.partial"
        with open(tmp, "wb") as fh:
            for chunk in resp.iter_content(1 << 20):
                fh.write(chunk)
    expects_html = name.lower().endswith((".html", ".htm"))
    if not expects_html and looks_like_html(tmp):
        tmp.unlink()
        raise ValueError("server returned an HTML page instead of a data file "
                         "(link moved, login wall, or Drive virus-scan page)")
    final = tmp.with_name(name)
    tmp.replace(final)
    return final


def acquire(ds: Dataset, year: int, manifest: Manifest, *, force: bool = False,
            dry_run: bool = False, sess: requests.Session | None = None) -> Result:
    if not ds.covers(year):
        return Result(ds, year, "not_covered", message=f"covers {ds.years[0]}-{ds.years[1]}")
    if ds.source_spec.get("edition_for_year") and ds.edition(year) is None:
        return Result(ds, year, "not_covered", message="no published edition contains this year yet")
    if ds.manual:
        where = ds.fill(ds.spec.get("where", ""), year)
        return Result(ds, year, "manual", message=where)

    prev = manifest.latest(ds.source, ds.key, ds.slot(year))
    if prev and not force and (ROOT / prev["file"]).exists():
        return Result(ds, year, "skipped", ROOT / prev["file"], prev["url"], "already in manifest")

    sess = sess or session()
    candidates: list[tuple[str, str]] = [(ds.fill(u, year), "") for u in ds.spec.get("urls", [])]
    tried: list[str] = []

    if dry_run:
        return Result(ds, year, "dry_run",
                      message="; ".join(u for u, _ in candidates) or "discovery on landing page")

    dest = target_dir(ds, year)
    errors = []
    for i in range(2):  # pass 0: direct urls; pass 1: discovery
        if i == 1:
            try:
                link = discover(ds, year, sess)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"discovery: {exc}")
                link = None
            candidates = [(link.url, link.text)] if link else []
        for url, text in candidates:
            tried.append(url)
            try:
                path = fetch(url, dest / ".incoming", sess)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{url}: {exc}")
                continue
            return _finalise(ds, year, path, url, text, manifest, prev)

    hint = ds.fill(ds.spec.get("where", ""), year)
    return Result(ds, year, "failed", url="", tried=tried,
                  message=" | ".join(errors) + (f" | manual: {hint}" if hint else ""))


def _finalise(ds: Dataset, year: int, incoming: Path, url: str, link_text: str,
              manifest: Manifest, prev: dict | None, method: str = "download",
              notes: str = "") -> Result:
    digest = sha256(incoming)
    final_dir = target_dir(ds, year)
    final = final_dir / incoming.name

    if prev and prev["sha256"] == digest and (ROOT / prev["file"]).exists():
        incoming.unlink()
        _cleanup(incoming.parent)
        old = ROOT / prev["file"]
        if old.name != final.name and not final.exists():   # same content, better name
            old.rename(final)
            prev["file"] = str(final.relative_to(ROOT))
            prev["notes"] = (prev["notes"] + f"; renamed from {old.name}").lstrip("; ")
            manifest.save()
            return Result(ds, year, "unchanged", final, url, f"renamed from {old.name}")
        return Result(ds, year, "unchanged", old, url, "same content as manifest")

    if final.exists():  # different content at same name -> keep old version
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        keep = RAW_DIR / "_superseded" / stamp / final.relative_to(RAW_DIR)
        keep.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(final), keep)
        for r in manifest.rows:
            if r["file"] == str(final.relative_to(ROOT)) and r["status"] == "current":
                r["file"] = str(keep.relative_to(ROOT))
    final_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(incoming), final)
    _cleanup(incoming.parent)

    manifest.append({
        "source": ds.source, "dataset": ds.key, "year": ds.slot(year),
        "edition": ds.edition(year) or "", "file": str(final.relative_to(ROOT)),
        "url": url, "link_text": link_text, "retrieved_at": now_iso(),
        "sha256": digest, "bytes": final.stat().st_size,
        "methodology": ds.spec.get("methodology", ""), "method": method,
        "status": "current", "notes": notes,
    })
    return Result(ds, year, "downloaded" if method == "download" else "registered", final, url)


def _cleanup(d: Path) -> None:
    if d.name == ".incoming" and d.exists() and not any(d.iterdir()):
        d.rmdir()


def register(ds: Dataset, year: int, file: Path, manifest: Manifest, *,
             url: str = "", notes: str = "") -> Result:
    """Copy a manually obtained file into data/raw and log it."""
    if not file.exists():
        raise FileNotFoundError(file)
    incoming = target_dir(ds, year) / ".incoming" / file.name
    incoming.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file, incoming)
    prev = manifest.latest(ds.source, ds.key, ds.slot(year))
    return _finalise(ds, year, incoming, url or f"manual:{file.name}", "", manifest, prev,
                     method="manual", notes=notes)
