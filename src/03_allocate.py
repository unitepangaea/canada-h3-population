"""03: build the PHH, NAR and HYB hexagon layers at one resolution (protocol B2).

  python 03_allocate.py --method v2 --variant base --res 8 [--no-gpkg] [--crs-variants]

Writes to output_v2/<tag>/res<r>/:
  contrib_long.parquet      DBUID, h3, pop_phh, pop_nar, pop_hyb, nar_tier, src_hyb
                            (Eq. 19 decompositions at any cell come from this table)
  {phh,nar,hyb}_h3_res<r>.parquet / .gpkg
                            h3, res, population, area_km2, pop_density_km2, n_dbs_contributing,
                            share_pop_from_phh_source (hyb), fallback_tier (nar), low_count_flag, geometry
  hyb_h3_res<r>_<crs>.gpkg  with --crs-variants (D3)
  allocate_summary.json, nar_fallback_tiers.csv, unallocated_dbs.csv (only if tier 3 occurs)

nar_tier / fallback_tier: 0 = location points, 1 = cell-centre fill, 2 = representative point;
for a hexagon, fallback_tier is the highest tier among its contributions.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from hexpop import core  # noqa: E402
from hexpop.io import Log  # noqa: E402

TOL = 1e-6


def allocate(st: C.RunSettings, r: int, log: Log) -> tuple[pd.DataFrame, dict]:
    hc = f"h3_{r}"
    db = pd.read_parquet(st.out_dir / "db_table.parquet", columns=["DBUID", "POP", "n", "zero_cov", "s_final"])
    db = db.set_index("DBUID")
    pop = db.POP
    summ: dict = {"tag": st.tag, "res": r, "P": float(pop.sum()), "populated_dbs": int((pop > 0).sum())}

    # PHH (Eq. 2)
    phh = pd.read_parquet(C.PHH_POINTS, columns=["DBUID", "pop", "in_universe", hc])
    if not st.phh_include_unpolygoned:
        phh = phh[phh.in_universe]
    log(f"[{st.tag} r={r}] PHH: {len(phh):,} points, total {phh['pop'].sum():,.3f}")

    # NAR points (Eq. 4), active filter
    nar = pd.read_parquet(C.NAR_POINTS, columns=[st.dbuid_col, "bu_class", hc]).rename(columns={st.dbuid_col: "DBUID"})
    nar = nar[nar.DBUID.notna() & nar.DBUID.isin(db.index)]
    if st.use_bu_filter:
        nar = nar[nar.bu_class.isin(list(st.bu_keep))]
    n_check = nar.groupby("DBUID").size().reindex(db.index).fillna(0)
    assert (n_check == db.n).all(), "n(d) differs from db_table; rerun 02_db_table.py"

    # NAR areal fallback (Eq. 5) on cartographic polygons
    zc = db.index[db.zero_cov]
    polys = gpd.read_parquet(C.DB_CARTO_4326)
    polys = polys[polys.DBUID.isin(zc)].set_index("DBUID").geometry

    lt, fb_c, unalloc = core.build_contributions(
        pop, db.s_final, polys,
        phh.DBUID.to_numpy(), phh["pop"].to_numpy(), phh[hc].to_numpy(),
        nar.DBUID.to_numpy(), nar[hc].to_numpy(), r)
    del phh, nar, polys

    tiers = fb_c.groupby("DBUID")["nar_tier"].max()
    tier_tab = pd.DataFrame({
        "n_dbs": tiers.value_counts().sort_index(),
        "pop": pop.reindex(tiers.index).groupby(tiers).sum(),
    }).rename_axis("tier")
    tier_tab.loc[3] = [len(unalloc), unalloc.POP.sum() if len(unalloc) else 0.0]
    tier_tab.to_csv(st.res_dir(r) / "nar_fallback_tiers.csv")
    log(f"[{st.tag} r={r}] NAR fallback: {len(zc):,} zero-coverage DBs\n{tier_tab.to_string()}")
    summ["fallback"] = {int(k): {"n_dbs": int(v["n_dbs"]), "pop": float(v["pop"])} for k, v in tier_tab.iterrows()}
    if len(unalloc):
        unalloc.to_csv(st.res_dir(r) / "unallocated_dbs.csv", index=False)
        log(f"!! {len(unalloc)} DBs could not be allocated (tier 3); see unallocated_dbs.csv")

    # Per-DB conservation (V1 preview)
    tot = core.db_totals(lt).reindex(db.index).fillna(0.0)
    for m in ("phh", "nar", "hyb"):
        eps = tot[f"pop_{m}"] - pop
        summ[f"max_abs_eps_{m}"] = float(eps.abs().max())
        summ[f"total_{m}"] = float(lt[f"pop_{m}"].sum())
        log(f"[{st.tag} r={r}] {m.upper()}: layer total {lt[f'pop_{m}'].sum():,.6f}; "
            f"max |eps(d)| over universe DBs {eps.abs().max():.2e}")
        assert eps.abs().max() < TOL, f"{m} conservation fails at r={r}"
    extra = lt.loc[~lt.DBUID.isin(db.index), "pop_phh"].sum()
    if extra:
        log(f"[{st.tag} r={r}] PHH layer includes {extra:,.3f} people in DBs outside the universe (v1 only)")
    summ["phh_outside_universe"] = float(extra)
    return lt, summ


def layers(lt: pd.DataFrame, st: C.RunSettings, r: int, log: Log, write_gpkg: bool, crs_variants: bool,
           summ: dict) -> None:
    rd = st.res_dir(r)
    # HYB-V changes only the hybrid layer; its PHH and NAR layers equal the base run's
    methods = ("hyb",) if st.hyb_v else ("phh", "nar", "hyb")
    tabs = {m: core.hex_table(lt, m, r, C.LOW_COUNT_THRESHOLD) for m in methods}
    cells = np.unique(np.concatenate([t.h3.to_numpy() for t in tabs.values()]))
    geom = gpd.GeoSeries(core.cell_polygons(cells), crs=4326)
    area = pd.Series(geom.to_crs(C.CRS_AREA).area.to_numpy() / 1e6, index=cells)
    geom.index = cells
    for m, t in tabs.items():
        ints = t.h3.to_numpy()
        t["area_km2"] = area.reindex(ints).to_numpy()
        t["pop_density_km2"] = t.population / t.area_km2
        g = geom.reindex(ints).to_numpy()
        t["h3"] = core.cells_to_str(ints)
        order = ["h3", "res", "population", "area_km2", "pop_density_km2", "n_dbs_contributing"] + \
                [c for c in ("share_pop_from_phh_source", "fallback_tier") if c in t] + ["low_count_flag"]
        gdf = gpd.GeoDataFrame(t[order], geometry=g, crs=4326)
        gdf.to_parquet(rd / f"{m}_h3_res{r}.parquet", index=False)
        if write_gpkg:
            gdf.to_file(rd / f"{m}_h3_res{r}.gpkg", driver="GPKG", layer=f"{m}_h3_res{r}")
        summ[f"n_cells_{m}"] = int(len(gdf))
        log(f"[{st.tag} r={r}] {m}: {len(gdf):,} populated cells; total {gdf.population.sum():,.3f}")
        if m == "hyb" and crs_variants:
            for name, crs in C.CRS_VARIANTS.items():
                gdf.to_crs(crs).to_file(rd / f"hyb_h3_res{r}_{name}.gpkg", driver="GPKG")
            log(f"[{st.tag} r={r}] hybrid CRS variants written: {list(C.CRS_VARIANTS)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--method", default=C.METHOD_VERSION, choices=list(C.METHODS))
    ap.add_argument("--variant", default="base", choices=C.VARIANTS)
    ap.add_argument("--res", type=int, required=True, choices=C.RESOLUTIONS)
    ap.add_argument("--no-gpkg", action="store_true", help="write parquet only (faster; for ablation runs)")
    ap.add_argument("--crs-variants", action="store_true", help="also export the hybrid layer in the three CRSs")
    args = ap.parse_args()
    st = C.settings(args.method, args.variant)
    if not (st.out_dir / "db_table.parquet").exists():
        raise SystemExit(f"Run 02_db_table.py --method {st.method} --variant {st.variant} first")
    rd = st.res_dir(args.res)
    rd.mkdir(parents=True, exist_ok=True)
    log = Log(rd / "03_allocate_log.txt")
    lt, summ = allocate(st, args.res, log)
    out = lt.copy()
    out["h3"] = core.cells_to_str(out.h3.to_numpy())
    out.to_parquet(rd / "contrib_long.parquet", index=False)
    log(f"Wrote contrib_long.parquet ({len(out):,} rows)")
    del out
    layers(lt, st, args.res, log, not args.no_gpkg, args.crs_variants, summ)
    (rd / "allocate_summary.json").write_text(json.dumps(summ, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
