"""01: prepare point tables shared by every method version and resolution.

Writes (data_int/):
  phh_points.parquet     DBUID, PR, pop, dwell_total, dwell_occ, type, lat, lon, h3_6, h3_7, h3_8, in_universe
  nar_points.parquet     LOC_GUID, lat, lon, pr, bu_class, n_addr_total, n_addr_res, h3_6, h3_7, h3_8,
                         DBUID_carto, DBUID_digital   (point-in-polygon, predicate "within", both files)
  db_carto_4326.parquet, db_digital_4326.parquet      DB polygons in EPSG:4326 after make_valid
  01_prepare_log.txt, pip_unassigned_by_pr.csv

Both point-in-polygon joins are stored, so each method version picks its boundary in config
(PIP_BOUNDARY) without re-running the join. H3 indices are int64.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from hexpop import core  # noqa: E402
from hexpop.io import Log, load_db_polygons, load_gaf  # noqa: E402


def prepare_phh(log: Log, universe: pd.Index, gaf_ids: pd.Index) -> None:
    parts = []
    for p in sorted(C.PHH_DIR.glob("*.csv")):
        df = pd.read_csv(p, usecols=list(C.PHH_COLS), encoding="utf-8-sig",
                         dtype={"DBUID_Ididu": str, "Pruid_Pridu": str})
        parts.append(df.rename(columns=C.PHH_COLS))
    phh = pd.concat(parts, ignore_index=True)
    for c in ("pop", "dwell_total", "dwell_occ"):
        phh[c] = pd.to_numeric(phh[c], errors="coerce").fillna(0.0)
    n0 = len(phh)
    phh = phh.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    log(f"PHH: {n0:,} points; dropped for missing lat/lon {n0 - len(phh):,}; total pop {phh['pop'].sum():,.3f}")
    missing = ~phh["DBUID"].isin(gaf_ids)
    assert not missing.any(), f"{missing.sum()} PHH points have a DBUID not in the GAF"
    log("PHH: every point's DBUID exists in the GAF")
    phh["in_universe"] = phh["DBUID"].isin(universe)
    out = phh.loc[~phh.in_universe]
    log(f"PHH points outside the DB universe: {len(out):,} in {out.DBUID.nunique()} DBs, pop {out['pop'].sum():,.3f}")
    for r in C.RESOLUTIONS:
        phh[f"h3_{r}"] = core.tag_cells(phh["lat"].to_numpy(), phh["lon"].to_numpy(), r)
        log(f"PHH tagged at r={r}: {phh[f'h3_{r}'].nunique():,} distinct cells")
    phh["type"] = phh["type"].astype("int8")
    phh.to_parquet(C.PHH_POINTS, index=False)
    log(f"Wrote {C.rel(C.PHH_POINTS)}")


def prepare_polygons(log: Log) -> None:
    for shp, out, name in [(C.DB_CARTO_SHP, C.DB_CARTO_4326, "cartographic"),
                           (C.DB_DIGITAL_SHP, C.DB_DIGITAL_4326, "digital")]:
        if out.exists():
            log(f"{name}: {out.name} exists, skipped")
            continue
        dbs = load_db_polygons(shp)
        types = dbs.geometry.geom_type.value_counts().to_dict()
        dbs.to_parquet(out, index=False)
        log(f"{name}: {len(dbs):,} DB polygons -> {out.name}; geometry types after make_valid {types}")


def prepare_nar(log: Log) -> None:
    nar = pd.read_parquet(C.NAR_LOCATIONS)
    log(f"NAR: {len(nar):,} locations from {C.NAR_LOCATIONS.name}")
    for r in C.RESOLUTIONS:
        nar[f"h3_{r}"] = core.tag_cells(nar["lat"].to_numpy(), nar["lon"].to_numpy(), r)
    for path, col, name in [(C.DB_CARTO_4326, "DBUID_carto", "cartographic"),
                            (C.DB_DIGITAL_4326, "DBUID_digital", "digital")]:
        dbs = gpd.read_parquet(path)
        idx, n_multi = core.points_in_polygons(nar["lon"].to_numpy(), nar["lat"].to_numpy(),
                                               dbs.geometry.to_numpy())
        ids = dbs["DBUID"].to_numpy()
        nar[col] = pd.array(np.where(idx >= 0, ids[np.clip(idx, 0, None)], None), dtype="string")
        log(f"PIP {name}: unassigned {int((idx < 0).sum()):,}; in more than one polygon {n_multi:,}")
        del dbs
    both = nar["DBUID_carto"].notna() & nar["DBUID_digital"].notna()
    diff = both & (nar["DBUID_carto"] != nar["DBUID_digital"])
    log(f"Locations assigned under both files: {int(both.sum()):,}; assigned to different DBs: {int(diff.sum()):,}")
    nar.to_parquet(C.NAR_POINTS, index=False)
    log(f"Wrote {C.rel(C.NAR_POINTS)}")

    res = nar["bu_class"].isin(list(C.BU_KEEP))
    tab = pd.DataFrame({
        "n_loc": nar.groupby("pr").size(),
        "unassigned_carto": nar["DBUID_carto"].isna().groupby(nar["pr"]).sum(),
        "unassigned_digital": nar["DBUID_digital"].isna().groupby(nar["pr"]).sum(),
        "n_loc_bu12": res.groupby(nar["pr"]).sum(),
        "unassigned_carto_bu12": (nar["DBUID_carto"].isna() & res).groupby(nar["pr"]).sum(),
        "unassigned_digital_bu12": (nar["DBUID_digital"].isna() & res).groupby(nar["pr"]).sum(),
    })
    tab.loc["Canada"] = tab.sum()
    tab.to_csv(C.DATA_INT / "pip_unassigned_by_pr.csv")
    log("Unassigned NAR locations by province:\n" + tab.to_string())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["phh", "polygons", "nar"], help="run one step")
    args = ap.parse_args()
    C.DATA_INT.mkdir(exist_ok=True)
    log = Log(C.DATA_INT / "01_prepare_log.txt")

    if args.only in (None, "polygons"):
        prepare_polygons(log)
    universe = pd.Index(pd.read_parquet(C.DB_CARTO_4326, columns=["DBUID"])["DBUID"])
    gaf = load_gaf()
    not_in_carto = gaf.loc[~gaf.DBUID.isin(universe) & (gaf.POP > 0), "DBUID"]
    assert set(not_in_carto) == C.EXCLUDED_DBUIDS, f"populated DBs outside the universe: {sorted(not_in_carto)}"
    log(f"DB universe: {len(universe):,} DBs (cartographic); populated {int((gaf.POP[gaf.DBUID.isin(universe)] > 0).sum()):,}; "
        f"P = {gaf.POP[gaf.DBUID.isin(universe)].sum():,.0f}; excluded populated DBs {sorted(C.EXCLUDED_DBUIDS)}")
    if args.only in (None, "phh"):
        prepare_phh(log, universe, pd.Index(gaf.DBUID))
    if args.only in (None, "nar"):
        prepare_nar(log)
    log.save()
    return 0


if __name__ == "__main__":
    sys.exit(main())
