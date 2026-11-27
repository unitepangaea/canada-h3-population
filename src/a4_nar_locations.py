"""Phase A4: build data_int/nar_locations_v2.parquet from NAR-202606 Locations + Addresses.

Fields required by the protocol: LOC_GUID, lat, lon, bu_class, n_addr_total, n_addr_res.
Extra fields kept for later phases: pr (from file name), n_addr_bu1..bu4, n_addr_bu_na.

bu_class = the most residential BU_USE code among the location's addresses, using the order
1 (Residential) > 2 (Partial residential) > 4 (Unknown) > 3 (Non residential).
Unknown ranks above Non residential so that the {1, 2, 4} sensitivity keeps a location that has
any unknown-use address. The base filter {1, 2} is unaffected by this choice.
bu_class is <NA> for a location with no address record.

Locations without BF representative coordinates are dropped from the main table (protocol A4.4)
and written to nar_locations_v2_noBF.parquet with their BG coordinates (parked item 12.4).

Logs: data_int/a4_nar_log.txt and data_int/a4_nar_counts_by_pr.csv
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

NAR_DIR = C.NAR_DIR
INT = C.DATA_INT
OUT = INT / "nar_locations_v2.parquet"
OUT_NOBF = INT / "nar_locations_v2_noBF.parquet"
LOG = INT / "a4_nar_log.txt"

CA_LAT_RANGE = (41, 84)
CA_LON_RANGE = (-142, -52)
# rank: lower = more residential
RANK = {1: 0, 2: 1, 4: 2, 3: 3}
UNRANK = {v: k for k, v in RANK.items()}

_log_lines: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)
    _log_lines.append(msg)


def pr_of(p: Path) -> str:
    return re.search(r"_(\d{2})(?:_part_\d+)?\.csv$", p.name).group(1)


def read_addresses() -> pd.DataFrame:
    parts = []
    for p in sorted((NAR_DIR / "Addresses").glob("Address_*.csv")):
        t0 = time.time()
        a = pd.read_csv(p, encoding="utf-8-sig", usecols=["LOC_GUID", "ADDR_GUID", "BU_USE"],
                        dtype={"LOC_GUID": str, "ADDR_GUID": str, "BU_USE": "float64"})
        n = len(a)
        n_dup = a["ADDR_GUID"].duplicated().sum()
        bu = a["BU_USE"]
        g = pd.DataFrame({
            "LOC_GUID": a["LOC_GUID"],
            "n_addr_total": 1,
            "n_addr_bu1": (bu == 1).astype("int32"),
            "n_addr_bu2": (bu == 2).astype("int32"),
            "n_addr_bu3": (bu == 3).astype("int32"),
            "n_addr_bu4": (bu == 4).astype("int32"),
            "n_addr_bu_na": (~bu.isin([1, 2, 3, 4])).astype("int32"),
            "rank": bu.map(RANK).fillna(99).astype("int16"),
        })
        agg = g.groupby("LOC_GUID", sort=False).agg(
            n_addr_total=("n_addr_total", "sum"), n_addr_bu1=("n_addr_bu1", "sum"),
            n_addr_bu2=("n_addr_bu2", "sum"), n_addr_bu3=("n_addr_bu3", "sum"),
            n_addr_bu4=("n_addr_bu4", "sum"), n_addr_bu_na=("n_addr_bu_na", "sum"),
            rank=("rank", "min"))
        parts.append(agg)
        log(f"  {p.name}: {n:,} addresses, {len(agg):,} locations, dup ADDR_GUID in file {n_dup:,} "
            f"({time.time() - t0:.0f}s)")
    allp = pd.concat(parts)
    # a location's addresses can straddle part files: re-aggregate
    out = allp.groupby(level=0).agg({"n_addr_total": "sum", "n_addr_bu1": "sum", "n_addr_bu2": "sum",
                                     "n_addr_bu3": "sum", "n_addr_bu4": "sum", "n_addr_bu_na": "sum",
                                     "rank": "min"})
    log(f"Addresses: {int(out.n_addr_total.sum()):,} records over {len(out):,} distinct LOC_GUIDs "
        f"({len(allp) - len(out):,} location rows merged across files)")
    return out


def read_locations() -> pd.DataFrame:
    parts = []
    for p in sorted((NAR_DIR / "Locations").glob("Location_*.csv")):
        l = pd.read_csv(p, encoding="utf-8-sig",
                        usecols=["LOC_GUID", "BF_REPPOINT_LATITUDE", "BF_REPPOINT_LONGITUDE",
                                 "BG_LATITUDE", "BG_LONGITUDE"],
                        dtype={"LOC_GUID": str})
        l["pr"] = pr_of(p)
        parts.append(l)
        log(f"  {p.name}: {len(l):,} locations")
    loc = pd.concat(parts, ignore_index=True).rename(columns={
        "BF_REPPOINT_LATITUDE": "lat", "BF_REPPOINT_LONGITUDE": "lon",
        "BG_LATITUDE": "bg_lat", "BG_LONGITUDE": "bg_lon"})
    return loc


def main() -> int:
    INT.mkdir(exist_ok=True)
    t0 = time.time()
    log(f"NAR source: {NAR_DIR}")
    log("Reading Locations...")
    loc = read_locations()
    n_loc = len(loc)
    n_dup_loc = loc["LOC_GUID"].duplicated().sum()
    log(f"Locations: {n_loc:,} rows; duplicated LOC_GUID {n_dup_loc:,}")
    if n_dup_loc:
        loc = loc.drop_duplicates("LOC_GUID")

    log("Reading Addresses (one file at a time, aggregated to location)...")
    addr = read_addresses()

    orphan = addr.index.difference(loc["LOC_GUID"])
    log(f"Address LOC_GUIDs with no Location record: {len(orphan):,} "
        f"({int(addr.loc[orphan, 'n_addr_total'].sum()):,} addresses)")

    loc = loc.join(addr, on="LOC_GUID")
    cnt_cols = ["n_addr_total", "n_addr_bu1", "n_addr_bu2", "n_addr_bu3", "n_addr_bu4", "n_addr_bu_na"]
    loc[cnt_cols] = loc[cnt_cols].fillna(0).astype("int32")
    loc["n_addr_res"] = (loc["n_addr_bu1"] + loc["n_addr_bu2"]).astype("int32")
    loc["bu_class"] = loc["rank"].map(UNRANK).astype("Int8")
    loc = loc.drop(columns="rank")
    log(f"Locations with no address record: {(loc.n_addr_total == 0).sum():,}")

    no_bf = loc["lat"].isna() | loc["lon"].isna()
    log(f"Dropped for missing BF coordinates: {no_bf.sum():,} "
        f"(of which with BG coordinates: {(no_bf & loc.bg_lat.notna() & loc.bg_lon.notna()).sum():,}; "
        f"residential addresses at these locations: {int(loc.loc[no_bf, 'n_addr_res'].sum()):,})")
    loc[no_bf].reset_index(drop=True).to_parquet(OUT_NOBF, index=False)
    loc = loc[~no_bf]

    in_box = loc["lat"].between(*CA_LAT_RANGE) & loc["lon"].between(*CA_LON_RANGE)
    log(f"Outside Canada lat/lon box {CA_LAT_RANGE} x {CA_LON_RANGE}: {(~in_box).sum():,} (dropped)")
    loc = loc[in_box]

    keep = ["LOC_GUID", "lat", "lon", "bu_class", "n_addr_total", "n_addr_res", "pr",
            "n_addr_bu1", "n_addr_bu2", "n_addr_bu3", "n_addr_bu4", "n_addr_bu_na"]
    loc = loc[keep].reset_index(drop=True)
    loc.to_parquet(OUT, index=False)
    log(f"Wrote {C.rel(OUT)}: {len(loc):,} locations")

    cls = loc["bu_class"].astype("string").fillna("none")
    log("Locations by bu_class (1=Res, 2=Partial res, 3=Non res, 4=Unknown, none=no address):")
    for k, v in cls.value_counts().sort_index().items():
        log(f"  {k}: {v:,}")
    log(f"Kept under BU {{1,2}}: {cls.isin(['1', '2']).sum():,}; under BU {{1,2,4}}: {cls.isin(['1', '2', '4']).sum():,}")
    tab = pd.crosstab(loc["pr"], cls, margins=True, margins_name="Canada")
    tab["addr_total"] = loc.groupby("pr")["n_addr_total"].sum()
    tab["addr_res"] = loc.groupby("pr")["n_addr_res"].sum()
    tab.loc["Canada", ["addr_total", "addr_res"]] = [loc.n_addr_total.sum(), loc.n_addr_res.sum()]
    tab.to_csv(INT / "a4_nar_counts_by_pr.csv")
    log(tab.to_string())
    log(f"Elapsed {time.time() - t0:.0f}s")
    LOG.write_text("\n".join(_log_lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
