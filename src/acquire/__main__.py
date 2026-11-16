"""Step 1 - Acquire raw data.

Usage (from the repo root):

    python -m src.acquire run --year 2025                 # all sources
    python -m src.acquire run --year 2024 --source dgis   # one source
    python -m src.acquire run --year 2025 --dry-run       # show what would be fetched
    python -m src.acquire run --year 2025 --force         # re-download, keep old versions

    python -m src.acquire status --year 2025              # what's in hand vs. missing
    python -m src.acquire check                           # test configured URLs / landing pages
    python -m src.acquire links sesnsp                    # list every link on a source's landing page

    python -m src.acquire register --source cnegsr --dataset solicitud_registros \
        --year 2025 --file ~/Downloads/respuesta.xlsx --url "PNT folio 330024..." \
        --notes "Response received 2026-12-01"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import core

ICON = {"downloaded": "✓", "registered": "✓", "unchanged": "=", "skipped": "·",
        "manual": "✋", "not_covered": "–", "failed": "✗", "dry_run": "?"}


def cmd_run(args) -> int:
    cfg = core.load_config()
    manifest = core.Manifest()
    sess = core.session()
    failures = 0
    for ds in core.iter_datasets(cfg, args.source):
        if args.dataset and ds.key != args.dataset:
            continue
        r = core.acquire(ds, args.year, manifest, force=args.force, dry_run=args.dry_run, sess=sess)
        failures += r.status == "failed"
        where = f" -> {r.path.relative_to(core.ROOT)}" if r.path else ""
        print(f"{ICON.get(r.status, '?')} {ds.source}/{ds.key} [{ds.slot(args.year)}] {r.status}{where}")
        if r.message and r.status in {"failed", "manual", "not_covered", "dry_run", "unchanged"}:
            print(f"    {r.message}")
    print(f"\nManifest: {core.MANIFEST_PATH.relative_to(core.ROOT)}")
    return 1 if failures else 0


def cmd_status(args) -> int:
    cfg = core.load_config()
    manifest = core.Manifest()
    print(f"{'source/dataset':42} {'slot':>6}  status")
    for ds in core.iter_datasets(cfg, args.source):
        if not ds.covers(args.year):
            state = "not covered by this dataset"
        else:
            row = manifest.latest(ds.source, ds.key, ds.slot(args.year))
            if row:
                state = f"OK  {row['retrieved_at'][:10]}  {row['method']}  {Path(row['file']).name}"
            else:
                state = "MISSING (manual)" if ds.manual else "MISSING"
        print(f"{ds.source + '/' + ds.key:42} {ds.slot(args.year):>6}  {state}")
    return 0


def cmd_check(args) -> int:
    """HEAD/GET each configured URL (for --year) and each landing page."""
    cfg = core.load_config()
    sess = core.session()
    seen = set()
    for ds in core.iter_datasets(cfg, args.source):
        if not ds.covers(args.year):
            continue
        urls = [ds.fill(u, args.year) for u in ds.spec.get("urls", [])]
        landing = ds.spec.get("landing") or ds.source_spec.get("landing")
        if landing:
            urls.append(ds.fill(landing, args.year))
        for u in urls:
            if u in seen:
                continue
            seen.add(u)
            try:
                resp = sess.get(core.gdrive_direct(u), stream=True, timeout=30)
                code = resp.status_code
                ctype = resp.headers.get("Content-Type", "")[:40]
                resp.close()
            except Exception as exc:  # noqa: BLE001
                code, ctype = "ERR", str(exc)[:60]
            is_page = u == (ds.fill(landing, args.year) if landing else None)
            flag = ""
            if code == 200 and not is_page and "html" in ctype.lower():
                flag = "  <-- web page, NOT the file (wrong link or share page)"
            print(f"{code!s:>4}  {ctype:40}  {u}{flag}")
    return 0


def cmd_links(args) -> int:
    cfg = core.load_config()
    spec = cfg["sources"][args.source]
    landing = args.url or spec.get("landing")
    if not landing:
        print("No landing page configured; pass --url")
        return 1
    for link in core.list_links(landing):
        if not args.grep or args.grep.lower() in f"{link.text} {link.url}".lower():
            print(f"{link.text[:70]:70}  {link.url}")
    return 0


def cmd_register(args) -> int:
    cfg = core.load_config()
    matches = [d for d in core.iter_datasets(cfg, args.source) if d.key == args.dataset]
    if not matches:
        print(f"Unknown dataset {args.source}/{args.dataset}. Add it to config/sources.yaml first.")
        return 1
    r = core.register(matches[0], args.year, Path(args.file).expanduser(), core.Manifest(),
                      url=args.url, notes=args.notes)
    print(f"{ICON[r.status]} {r.status}: {r.path.relative_to(core.ROOT) if r.path else ''}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m src.acquire", description="Step 1: acquire raw data")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="download datasets for a year")
    r.add_argument("--year", type=int, required=True)
    r.add_argument("--source")
    r.add_argument("--dataset")
    r.add_argument("--force", action="store_true")
    r.add_argument("--dry-run", action="store_true")
    r.set_defaults(func=cmd_run)

    s = sub.add_parser("status", help="show what is in hand for a year")
    s.add_argument("--year", type=int, required=True)
    s.add_argument("--source")
    s.set_defaults(func=cmd_status)

    c = sub.add_parser("check", help="test configured URLs and landing pages")
    c.add_argument("--year", type=int, default=2025)
    c.add_argument("--source")
    c.set_defaults(func=cmd_check)

    l = sub.add_parser("links", help="list links on a source's landing page")
    l.add_argument("source")
    l.add_argument("--url")
    l.add_argument("--grep")
    l.set_defaults(func=cmd_links)

    g = sub.add_parser("register", help="log a manually obtained file")
    g.add_argument("--source", required=True)
    g.add_argument("--dataset", required=True)
    g.add_argument("--year", type=int, required=True)
    g.add_argument("--file", required=True)
    g.add_argument("--url", default="")
    g.add_argument("--notes", default="")
    g.set_defaults(func=cmd_register)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
