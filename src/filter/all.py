"""Run every Step 2 filter for one reference year.

    python -m src.filter.all --year 2024

CJM and DGIS use --year directly; SESNSP picks the year from its 2015-2025 series;
ENDIREH has no annual data, so the latest edition (2021) is used for every year.
A source that fails is reported and the others still run.
"""

from __future__ import annotations

import argparse
import sys

from src.filter import cjm, dgis, endireh, sesnsp


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Step 2: run all filters")
    p.add_argument("--year", type=int, default=2024)
    p.add_argument("--endireh-edition", type=int, default=2021)
    args = p.parse_args(argv)

    steps = [("SESNSP", sesnsp.main, ["--year", str(args.year)]),
             ("CJM", cjm.main, ["--year", str(args.year)]),
             ("DGIS", dgis.main, ["--year", str(args.year)]),
             ("ENDIREH", endireh.main, ["--edition", str(args.endireh_edition)])]
    failed = []
    for name, fn, a in steps:
        print(f"\n===== {name} =====")
        try:
            fn(a)
        except SystemExit as e:
            if e.code not in (0, None):
                print(f"  ✗ {name} skipped: {e}")
                failed.append(name)
    print(f"\nStep 2 done for {args.year}. " + (f"Failed: {', '.join(failed)}" if failed else "All sources ran."))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
