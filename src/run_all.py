"""Run the pipeline for one or more method versions, variants and resolutions.

  python run_all.py --method v1 --res 8
  python run_all.py --method v2 --res 6 7 8 --variant base hybv --crs-variants
  python run_all.py --method v1 v1_M1 v1_M2 v2 --res 8 --no-gpkg          # D1 ablation

Runs 01_prepare_points.py if its outputs are missing (or with --prepare), then 02_db_table.py
once per method x variant and 03_allocate.py per resolution. Steps 04 to 08 belong to Phases E to G.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import config as C  # noqa: E402


def run(script: str, *args: str) -> None:
    cmd = [sys.executable, str(HERE / script), *args]
    print(">>", " ".join(cmd[1:]), flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--method", nargs="+", default=[C.METHOD_VERSION], choices=list(C.METHODS))
    ap.add_argument("--variant", nargs="+", default=["base"], choices=C.VARIANTS)
    ap.add_argument("--res", nargs="+", type=int, default=C.RESOLUTIONS, choices=C.RESOLUTIONS)
    ap.add_argument("--prepare", action="store_true", help="re-run 01_prepare_points.py")
    ap.add_argument("--no-gpkg", action="store_true")
    ap.add_argument("--crs-variants", action="store_true")
    args = ap.parse_args()

    needed = [C.PHH_POINTS, C.NAR_POINTS, C.DB_CARTO_4326, C.DB_DIGITAL_4326]
    if args.prepare or not all(p.exists() for p in needed):
        run("01_prepare_points.py")
    for m in args.method:
        for v in args.variant:
            try:
                C.settings(m, v)
            except ValueError as e:
                print(f"skip {m}/{v}: {e}")
                continue
            run("02_db_table.py", "--method", m, "--variant", v)
            for r in args.res:
                extra = (["--no-gpkg"] if args.no_gpkg else []) + (["--crs-variants"] if args.crs_variants else [])
                run("03_allocate.py", "--method", m, "--variant", v, "--res", str(r), *extra)
    return 0


if __name__ == "__main__":
    sys.exit(main())
