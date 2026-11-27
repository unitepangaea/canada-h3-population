"""Phase A2: verify the re-downloaded PHH 2021 release and write data_raw/MANIFEST.csv.

Acceptance (protocol Section 3, A2):
  - required columns present
  - row count = 16,614,053 (preprint Table 1)
  - for each DB, sum(Pop2021) == GAF DBPOP2021 within 1e-6

Writes:
  data_raw/MANIFEST.csv              (appends/updates rows for files under data_raw/)
  data_int/a2_phh_check_by_pr.csv    (row counts and population by province)
  data_int/a2_phh_db_mismatch.csv    (DBs failing the 1e-6 test, if any)
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

PHH_DIR = C.PHH_DIR
GAF_CSV = C.GAF_CSV
MANIFEST = C.DATA_RAW / "MANIFEST.csv"
INT = C.DATA_INT

REQUIRED = ["Pop2021", "TDwell2021_TLog2021", "URDwell2021_RH2021", "DBUID_Ididu",
            "Pruid_Pridu", "Latitude", "Longitude", "Type"]
EXPECTED_ROWS = 16_614_053
EXPECTED_POP = 36_991_971
EXPECTED_POP_DBS = 384_284
TOL = 1e-6

PHH_URL = "https://ised-isde.canada.ca/app/scr/sittibc/web/api/openData/PHH_2021_CSV.zip"
DICT_URL = "https://ised-isde.canada.ca/app/scr/sittibc/web/api/openData/PHH_data_dictionary_e.txt"


def sha256(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def update_manifest(rows: list[dict]) -> None:
    fields = ["file", "source_url", "download_date", "bytes", "sha256", "note"]
    existing: dict[str, dict] = {}
    if MANIFEST.exists():
        with open(MANIFEST, newline="") as f:
            for r in csv.DictReader(f):
                existing[r["file"]] = r
    for r in rows:
        existing[r["file"]] = r
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for k in sorted(existing):
            w.writerow(existing[k])


def main() -> int:
    INT.mkdir(exist_ok=True)
    zip_path = PHH_DIR.parent / "PHH_2021_CSV.zip"
    dict_path = PHH_DIR.parent / "PHH_data_dictionary_e.txt"
    today = dt.date.fromtimestamp(zip_path.stat().st_mtime).isoformat()
    note = "ISED Pseudo-Household Demographic Distribution 2021; open.canada.ca dataset b3a1d603-19ca-466c-ae95-b5185e56addf"
    man = [
        {"file": str(zip_path.relative_to(C.DATA_RAW)), "source_url": PHH_URL, "download_date": today,
         "bytes": zip_path.stat().st_size, "sha256": sha256(zip_path), "note": note},
        {"file": str(dict_path.relative_to(C.DATA_RAW)), "source_url": DICT_URL, "download_date": today,
         "bytes": dict_path.stat().st_size, "sha256": sha256(dict_path), "note": "PHH data dictionary (EN)"},
    ]
    for p in sorted(PHH_DIR.glob("*.csv")):
        man.append({"file": str(p.relative_to(C.DATA_RAW)), "source_url": f"{PHH_URL} (extracted)",
                    "download_date": today, "bytes": p.stat().st_size, "sha256": sha256(p), "note": "extracted from PHH_2021_CSV.zip"})
    update_manifest(man)
    print(f"MANIFEST updated: {len(man)} PHH entries")

    ok = True
    parts = []
    for p in sorted(PHH_DIR.glob("*.csv")):
        hdr = pd.read_csv(p, nrows=0, encoding="utf-8-sig").columns.tolist()
        missing = [c for c in REQUIRED if c not in hdr]
        if missing:
            print(f"FAIL {p.name}: missing columns {missing}")
            ok = False
            continue
        df = pd.read_csv(p, encoding="utf-8-sig", usecols=["DBUID_Ididu", "Pruid_Pridu", "Pop2021"],
                         dtype={"DBUID_Ididu": str, "Pruid_Pridu": str, "Pop2021": "float64"})
        df["file"] = p.name
        parts.append(df)
    phh = pd.concat(parts, ignore_index=True)
    n = len(phh)
    print(f"PHH rows: {n:,} (expected {EXPECTED_ROWS:,}) -> {'OK' if n == EXPECTED_ROWS else 'MISMATCH'}")
    ok &= n == EXPECTED_ROWS
    print(f"PHH total Pop2021: {phh.Pop2021.sum():,.6f} (expected {EXPECTED_POP:,})")

    by_pr = phh.groupby(["file", "Pruid_Pridu"]).agg(rows=("Pop2021", "size"), pop=("Pop2021", "sum")).reset_index()
    by_pr.to_csv(INT / "a2_phh_check_by_pr.csv", index=False)

    phh_db = phh.groupby("DBUID_Ididu")["Pop2021"].sum()

    gaf = pd.read_csv(GAF_CSV, usecols=["DBUID_IDIDU", "DBPOP2021_IDPOP2021"],
                      dtype={"DBUID_IDIDU": str}, encoding="latin1")
    gaf["DBPOP2021_IDPOP2021"] = pd.to_numeric(gaf["DBPOP2021_IDPOP2021"], errors="coerce").fillna(0)
    gaf_db = gaf.groupby("DBUID_IDIDU")["DBPOP2021_IDPOP2021"].first()
    print(f"GAF rows: {len(gaf):,}; unique DBs: {gaf_db.size:,}; populated DBs: {(gaf_db > 0).sum():,} "
          f"(expected {EXPECTED_POP_DBS:,}); total pop {gaf_db.sum():,.0f}")

    not_in_gaf = phh_db.index.difference(gaf_db.index)
    print(f"PHH DBUIDs not in GAF: {len(not_in_gaf):,}")
    ok &= len(not_in_gaf) == 0

    cmp = pd.DataFrame({"gaf_pop": gaf_db}).join(phh_db.rename("phh_pop"), how="outer").fillna(0.0)
    cmp["diff"] = cmp["phh_pop"] - cmp["gaf_pop"]
    bad = cmp[np.abs(cmp["diff"]) > TOL]
    print(f"DBs with |sum(Pop2021) - DBPOP2021| > {TOL}: {len(bad):,}; max |diff| = {np.abs(cmp['diff']).max():.3e}")
    print(f"  among populated GAF DBs: {(bad.gaf_pop > 0).sum():,}; population of those DBs: {bad.gaf_pop.sum():,.0f}")
    bad.reset_index(names="DBUID").to_csv(INT / "a2_phh_db_mismatch.csv", index=False)
    if len(bad):
        bad2 = bad.copy()
        bad2["PR"] = bad2.index.str[:2]
        print(bad2.groupby("PR").agg(n=("diff", "size"), gaf=("gaf_pop", "sum"), phh=("phh_pop", "sum"),
                                       sum_diff=("diff", "sum")).to_string())
    ok &= len(bad) == 0

    print("ACCEPT A2:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
