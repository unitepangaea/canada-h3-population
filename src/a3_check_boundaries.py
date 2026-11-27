"""Phase A3: compare DBUID sets in the digital (ldb_000a21a_e) and cartographic (ldb_000b21a_e) DB files.

Acceptance: both DB files contain the same DBUID set. Also compared against the GAF.
Expects the digital file at data_raw/ldb_000a21a_e/ (the .zip, or the extracted .shp).
Adds the digital file to data_raw/MANIFEST.csv.

Writes data_int/a3_dbuid_set_diff.csv (DBUIDs not in all three sources, with GAF population).
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pyogrio

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

DIG_DIR = C.DB_DIGITAL_SHP.parent
CARTO_SHP = C.DB_CARTO_SHP
PROV = C.PROV_GPKG
GAF_CSV = C.GAF_CSV
MANIFEST = C.DATA_RAW / "MANIFEST.csv"
INT = C.DATA_INT
URL = "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/ldb_000a21a_e.zip"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(1 << 22):
            h.update(b)
    return h.hexdigest()


def add_manifest(path: Path, note: str) -> None:
    fields = ["file", "source_url", "download_date", "bytes", "sha256", "note"]
    rows = {}
    if MANIFEST.exists():
        with open(MANIFEST, newline="") as f:
            rows = {r["file"]: r for r in csv.DictReader(f)}
    key = str(path.relative_to(C.DATA_RAW))
    rows[key] = {"file": key, "source_url": URL, "download_date": dt.date.fromtimestamp(path.stat().st_mtime).isoformat(),
                 "bytes": path.stat().st_size, "sha256": sha256(path), "note": note}
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for k in sorted(rows):
            w.writerow(rows[k])


def main() -> int:
    zips = list(DIG_DIR.glob("*.zip"))
    if zips:
        add_manifest(zips[0], "StatCan 2021 DB digital boundary file (manual download by Paul; site blocks scripted clients)")
        if not list(DIG_DIR.glob("*.shp")):
            zipfile.ZipFile(zips[0]).extractall(DIG_DIR)
    shps = list(DIG_DIR.rglob("*.shp"))
    if not shps:
        print(f"Digital DB file not found under {DIG_DIR}")
        return 2
    dig = pyogrio.read_dataframe(shps[0], columns=["DBUID"], read_geometry=False)
    car = pyogrio.read_dataframe(CARTO_SHP, columns=["DBUID"], read_geometry=False)
    gaf = pd.read_csv(GAF_CSV, usecols=["DBUID_IDIDU", "DBPOP2021_IDPOP2021"], dtype={"DBUID_IDIDU": str}, encoding="latin1")
    gaf["pop"] = pd.to_numeric(gaf["DBPOP2021_IDPOP2021"], errors="coerce").fillna(0)
    print(f"digital: {len(dig):,} rows / {dig.DBUID.nunique():,} unique; CRS {pyogrio.read_info(shps[0])['crs']}")
    print(f"cartographic: {len(car):,} rows / {car.DBUID.nunique():,} unique")
    print(f"GAF: {len(gaf):,} DBs")
    print(f"province_boundaries.gpkg present: {PROV.exists()}")

    d, c, g = set(dig.DBUID), set(car.DBUID), set(gaf.DBUID_IDIDU)
    allid = d | c | g
    diff = pd.DataFrame({"DBUID": sorted(allid)})
    diff["in_digital"] = diff.DBUID.isin(d)
    diff["in_carto"] = diff.DBUID.isin(c)
    diff["in_gaf"] = diff.DBUID.isin(g)
    diff = diff[~(diff.in_digital & diff.in_carto & diff.in_gaf)].merge(
        gaf[["DBUID_IDIDU", "pop"]].rename(columns={"DBUID_IDIDU": "DBUID"}), on="DBUID", how="left")
    INT.mkdir(exist_ok=True)
    diff.to_csv(INT / "a3_dbuid_set_diff.csv", index=False)
    print(f"digital - carto: {len(d - c):,}; carto - digital: {len(c - d):,}")
    print(f"GAF - digital: {len(g - d):,}; digital - GAF: {len(d - g):,}")
    print(f"GAF - carto: {len(g - c):,} (population {diff.loc[~diff.in_carto & diff.in_gaf, 'pop'].sum():,.0f})")
    same = d == c
    print("ACCEPT A3 (identical DBUID sets):", "PASS" if same else "FAIL")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
