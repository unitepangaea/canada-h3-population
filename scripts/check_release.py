"""
check_release.py

Pre-release checks on the files in release/:

  1. Every column listed in docs/DATA_DICTIONARY.md exists in the files, and
     every file column is documented.
  2. Hexagon layers conserve the national population.
  3. Block totals are conserved: summing each contribution table by DBUID
     reproduces the block population for every method.
  4. The hybrid source is identical at every resolution (checked through the
     contribution tables: each block's hybrid total is the same at r = 6, 7, 8).

Usage (from the repository root):  python scripts/check_release.py --version v2
Writes docs/validation_<version>_release.md and exits non-zero on failure.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
RELEASE = REPO / "release"
NATIONAL_POP = 36_991_971
TOL_NAT = 1e-3
TOL_DB = 1e-6


def documented_columns() -> dict[str, set[str]]:
    """Parse the column tables in the data dictionary, by section."""
    text = (REPO / "docs" / "DATA_DICTIONARY.md").read_text()
    sections = {"hex": "## 4.", "db": "## 5.", "contrib": "## 6."}
    out = {}
    for key, head in sections.items():
        start = text.index(head)
        end = text.find("\n## ", start + 1)
        block = text[start:end if end > 0 else None]
        cols = set()
        for cell in re.findall(r"^\| (`[^|]+?`) \|", block, flags=re.M):
            # Expand entries such as `CSDUID`, `CMAUID`, `POPCTRUID`
            cols.update(c.strip(" ") if "…" in c else c.strip(" `")
                        for c in cell.split(","))
        out[key] = cols
    return out


def expand_ranges(cols: set[str], actual: set[str]) -> set[str]:
    """Treat documented 'a … b' entries as matching any actual column with that stem."""
    keep = {c for c in cols if "…" not in c}
    for c in cols - keep:
        first, last = (part.strip(" `") for part in c.split("…"))
        stem = os.path.commonprefix([first, last]).rstrip("0123456789")
        keep.add(first)
        keep.add(last)
        keep.update(a for a in actual if a.startswith(stem))
    return keep


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v2")
    v = ap.parse_args().version
    docs = documented_columns()
    lines, failures = [f"# Release checks, method {v}\n"], 0

    def report(ok: bool, msg: str) -> None:
        nonlocal failures
        failures += not ok
        lines.append(f"- {'PASS' if ok else 'FAIL'}: {msg}")

    # 1-2. Hexagon layers
    lines.append("\n## Hexagon layers\n")
    for f in sorted(RELEASE.glob(f"hexpop_*_{v}_res*.parquet")):
        actual = set(pq.read_schema(f).names)
        # Method-specific columns are documented but present only in some layers
        optional = {"share_pop_from_phh_source", "fallback_tier"}
        expected = docs["hex"]
        missing = (expected - optional) - actual
        undocumented = actual - expected
        report(not missing and not undocumented,
               f"{f.name} columns (missing {sorted(missing) or 'none'}, "
               f"undocumented {sorted(undocumented) or 'none'})")
        total = pd.read_parquet(f, columns=["population"])["population"].sum()
        report(abs(total - NATIONAL_POP) <= TOL_NAT, f"{f.name} national total {total:,.3f}")

    # 3. Block table and conservation
    lines.append("\n## Block-level conservation\n")
    db = pd.read_parquet(RELEASE / f"db_table_{v}.parquet")
    actual = set(db.columns)
    expected = expand_ranges(docs["db"], actual)
    report(not (expected - actual) and not (actual - expected),
           f"db_table columns (missing {sorted(expected - actual) or 'none'}, "
           f"undocumented {sorted(actual - expected) or 'none'})")

    hyb_by_res = {}
    for f in sorted(RELEASE.glob(f"contributions_{v}_res*.parquet")):
        c = pd.read_parquet(f)
        res = f.stem.split("res")[-1]
        report(set(c.columns) == docs["contrib"], f"{f.name} columns")
        sums = c.groupby("DBUID")[["pop_phh", "pop_nar", "pop_hyb"]].sum()
        merged = sums.join(db.set_index("DBUID")["POP"], how="outer").fillna(0)
        for m in ["pop_phh", "pop_nar", "pop_hyb"]:
            err = (merged[m] - merged["POP"]).abs().max()
            report(err < TOL_DB, f"res {res} {m}: max block error {err:.2e}")
        hyb_by_res[res] = sums["pop_hyb"]

    # 4. Cross-resolution invariance
    lines.append("\n## Cross-resolution invariance\n")
    keys = sorted(hyb_by_res)
    for a, b in zip(keys, keys[1:]):
        diff = (hyb_by_res[a] - hyb_by_res[b]).abs().max()
        report(diff < TOL_DB, f"hybrid block totals, res {a} vs res {b}: max difference {diff:.2e}")

    out = REPO / "docs" / f"validation_{v}_release.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\n{failures} failure(s). Report written to {out.relative_to(REPO)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
