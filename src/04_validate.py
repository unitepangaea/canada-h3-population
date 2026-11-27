"""04: Phase E validation (V1 to V6) for the headline v2 layers and the HYB-V hybrid.

  python 04_validate.py [--skip-v6]

V1  DB-level conservation, each method x r: max_d |eps(d)| < 1e-6
V2  province conservation (Eq. 8), each method x r: |eps(p)| < 1e-6; national total 36,991,971
V3  cross-resolution invariance: s(d) and each DB's total contribution identical at r = 6, 7, 8
V4  non-nesting: res-8 layers aggregated with cell_to_parent vs the directly binned res-7 and res-6 layers
    (and res 7 -> 6); report only
V5  NAR fallback diagnostics by r: tier counts, NAR-only cells, cells with population < 1; tier 3 = 0
V6  hierarchical accuracy test by r: DA population disaggregated to cells with v2 NAR location weights
    (DA-level two-tier fallback for DAs without locations), and an areal-weighting baseline
    (equal shares to cells whose centre lies in the DA, tier 2 for slivers), each compared with the
    DB-based NAR v2 layer M at the same r. PHH cannot be tested this way: its point populations
    already encode DB totals.

Writes tables/validation_V{1..6}_*.csv and tables/validation_summary.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import h3
import h3.api.basic_int as h3i
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from hexpop import core  # noqa: E402
from hexpop import metrics as M  # noqa: E402
from hexpop.io import Log  # noqa: E402

TOL = 1e-6
INV_TOL = 1e-9          # "exact" up to floating-point summation order
RUNS = [(C.settings("v2", "base"), ("phh", "nar", "hyb")), (C.settings("v2", "hybv"), ("hyb",))]
DA_4326 = C.DATA_INT / "da_carto_4326.parquet"


def load_lt(st, r):
    return pd.read_parquet(st.res_dir(r) / "contrib_long.parquet")


def v1_v2_v3(log: Log):
    v1, v2, v3 = [], [], []
    for st, methods in RUNS:
        db = pd.read_parquet(st.out_dir / "db_table.parquet", columns=["DBUID", "POP", "PR", "s_final"]).set_index("DBUID")
        prov = db.groupby("PR").POP.sum()
        totals, srcs = {}, {}
        for r in C.RESOLUTIONS:
            lt = load_lt(st, r)
            tot = core.db_totals(lt).reindex(db.index).fillna(0.0)
            totals[r] = tot
            srcs[r] = lt.loc[lt.pop_hyb > 0].groupby("DBUID").src_hyb.agg(lambda s: "|".join(sorted(set(map(str, s)))))
            for m in methods:
                eps = tot[f"pop_{m}"] - db.POP
                v1.append({"tag": st.tag, "method": m, "res": r, "n_dbs": len(eps),
                           "max_abs_eps": eps.abs().max(), "n_dbs_over_tol": int((eps.abs() > TOL).sum()),
                           "pass": bool(eps.abs().max() < TOL)})
                lp = tot[f"pop_{m}"].groupby(db.PR).sum()
                for pr in prov.index:
                    v2.append({"tag": st.tag, "method": m, "res": r, "PR": pr, "gaf_pop": prov[pr],
                               "layer_pop": lp.get(pr, 0.0), "eps": lp.get(pr, 0.0) - prov[pr]})
                v2.append({"tag": st.tag, "method": m, "res": r, "PR": "Canada", "gaf_pop": prov.sum(),
                           "layer_pop": lt[f"pop_{m}"].sum(), "eps": lt[f"pop_{m}"].sum() - C.EXPECTED_P})
        for m in methods:
            d = max(float((totals[r][f"pop_{m}"] - totals[C.RESOLUTIONS[0]][f"pop_{m}"]).abs().max())
                    for r in C.RESOLUTIONS[1:])
            v3.append({"tag": st.tag, "check": f"DB total contribution, {m}", "max_abs_diff_across_r": d,
                       "pass": d < INV_TOL})
        base = srcs[C.RESOLUTIONS[0]]
        same = all(srcs[r].sort_index().equals(base.sort_index()) for r in C.RESOLUTIONS[1:])
        mixed = int(sum((srcs[r].str.contains("\\|")).sum() for r in C.RESOLUTIONS))
        agree_tab = all((srcs[r] == db.s_final.astype(str).reindex(srcs[r].index)).all() for r in C.RESOLUTIONS)
        v3.append({"tag": st.tag, "check": "hybrid source s(d) per DB", "max_abs_diff_across_r": 0.0 if same else np.nan,
                   "pass": bool(same and mixed == 0 and agree_tab),
                   "note": f"identical across r: {same}; DBs with mixed sources: {mixed}; equals db_table s_final: {agree_tab}"})
        log(f"V1-V3 {st.tag} done")
    v1, v2, v3 = pd.DataFrame(v1), pd.DataFrame(v2), pd.DataFrame(v3)
    v2["pass"] = v2.eps.abs() < TOL
    v1.to_csv(C.TABLES / "validation_V1_db_conservation.csv", index=False)
    v2.to_csv(C.TABLES / "validation_V2_province_conservation.csv", index=False)
    v3.to_csv(C.TABLES / "validation_V3_invariance.csv", index=False)
    return v1, v2, v3


def to_parent(cells: pd.Series, pr: int) -> pd.Series:
    """cells indexed by H3 string -> totals by parent at resolution pr."""
    parents = [h3.cell_to_parent(c, pr) for c in cells.index]
    return cells.groupby(np.asarray(parents)).sum()


def v4(log: Log) -> pd.DataFrame:
    rows = []
    for st, methods in RUNS:
        layers = {r: load_lt(st, r).groupby("h3")[[f"pop_{m}" for m in methods]].sum() for r in C.RESOLUTIONS}
        for fine, coarse in [(8, 7), (8, 6), (7, 6)]:
            for m in methods:
                agg = to_parent(layers[fine][f"pop_{m}"][layers[fine][f"pop_{m}"] > 0], coarse)
                direct = layers[coarse][f"pop_{m}"]
                df = M.pair_frame(direct, agg)
                d = (df.y - df.x).abs()
                rows.append({"tag": st.tag, "method": m, "from_res": fine, "to_res": coarse,
                             "cells_direct": int((direct > 0).sum()), "cells_aggregated": int((agg > 0).sum()),
                             "cells_union": len(df), "D": M.displaced(df)["D"], "D_over_P_pct": 100 * M.displaced(df)["D_over_P"],
                             "n_cells_diff_gt1": int((d > 1).sum()), "pct_cells_diff_gt1": 100 * (d > 1).mean(),
                             "max_abs_diff": d.max(), "cell_max_abs_diff": d.idxmax()})
        log(f"V4 {st.tag} done")
    t = pd.DataFrame(rows)
    t.to_csv(C.TABLES / "validation_V4_nesting.csv", index=False)
    return t


def v5(log: Log) -> pd.DataFrame:
    st = C.settings("v2")
    rows = []
    for r in C.RESOLUTIONS:
        tiers = pd.read_csv(st.res_dir(r) / "nar_fallback_tiers.csv", index_col="tier")
        cells = load_lt(st, r).groupby("h3")[["pop_phh", "pop_nar", "pop_hyb"]].sum()
        row = {"res": r}
        for t in (1, 2, 3):
            row[f"tier{t}_dbs"] = int(tiers.n_dbs.get(t, 0))
            row[f"tier{t}_pop"] = float(tiers["pop"].get(t, 0.0))
        row["nar_only_cells"] = int(((cells.pop_nar > 0) & (cells.pop_phh == 0)).sum())
        row["nar_only_pop"] = cells.pop_nar[(cells.pop_nar > 0) & (cells.pop_phh == 0)].sum()
        for m in ("phh", "nar", "hyb"):
            c = cells[f"pop_{m}"]
            row[f"{m}_cells"] = int((c > 0).sum())
            row[f"{m}_cells_lt1"] = int(((c > 0) & (c < 1)).sum())
            row[f"{m}_pct_cells_lt1"] = 100 * row[f"{m}_cells_lt1"] / row[f"{m}_cells"]
        row["pass_tier3_zero"] = row["tier3_dbs"] == 0
        rows.append(row)
    t = pd.DataFrame(rows)
    t.to_csv(C.TABLES / "validation_V5_fallback.csv", index=False)
    log("V5 done")
    return t


def da_polygons(log: Log) -> pd.Series:
    if not DA_4326.exists():
        da = gpd.read_file(C.DA_CARTO_SHP, columns=["DAUID"]).to_crs(4326)
        da["geometry"] = da.geometry.make_valid()
        da.to_parquet(DA_4326, index=False)
        log(f"DA polygons cached: {len(da):,}")
    da = gpd.read_parquet(DA_4326)
    return da.set_index("DAUID").geometry


def err_metrics(est: pd.Series, ref: pd.Series) -> dict:
    df = M.pair_frame(ref, est)          # x = reference M, y = estimate
    e = df.y - df.x
    big = df.x >= 5
    return {"cells_union": len(df), "MAE": e.abs().mean(), "RMSE": float(np.sqrt((e ** 2).mean())),
            "median_APE_M5": float((e.abs()[big] / df.x[big]).median()), "n_cells_M5": int(big.sum()),
            "D_over_P_pct": 100 * M.displaced(df)["D_over_P"]}


def v6(log: Log) -> pd.DataFrame:
    st = C.settings("v2")
    db = pd.read_parquet(st.out_dir / "db_table.parquet", columns=["DBUID", "DAUID", "POP"])
    da_pop = db.groupby("DAUID").POP.sum()
    nar = pd.read_parquet(C.NAR_POINTS, columns=[st.dbuid_col, "bu_class"] + [f"h3_{r}" for r in C.RESOLUTIONS])
    nar = nar.rename(columns={st.dbuid_col: "DBUID"})
    nar = nar[nar.DBUID.notna() & nar.bu_class.isin(list(st.bu_keep))]
    nar["DAUID"] = nar.DBUID.map(db.set_index("DBUID").DAUID)
    nar = nar[nar.DAUID.notna()]
    n_da = nar.groupby("DAUID").size().reindex(da_pop.index).fillna(0)
    zero_da = da_pop.index[(da_pop > 0) & (n_da == 0)]
    geoms = da_polygons(log)
    log(f"V6: {int((da_pop > 0).sum()):,} populated DAs; {len(zero_da):,} without active NAR locations")
    rows = []
    for r in C.RESOLUTIONS:
        ref = load_lt(st, r).groupby("h3").pop_nar.sum()
        ref.index = [h3.str_to_int(c) for c in ref.index]
        pts = core.nar_point_contrib(nar.DAUID.to_numpy(), nar[f"h3_{r}"].to_numpy(), da_pop)
        fb, un1 = core.areal_fallback(geoms.reindex(zero_da), da_pop, r)
        est_nar = pd.concat([pts, fb]).groupby("h3").pop_nar.sum()
        aw, un2 = core.areal_fallback(geoms.reindex(da_pop.index[da_pop > 0]), da_pop, r)
        est_aw = aw.groupby("h3").pop_nar.sum()
        for name, est, un in [("DA NAR-location weights (v2)", est_nar, un1), ("DA areal weighting (cell centres)", est_aw, un2)]:
            row = {"res": r, "estimator": name, "total": est.sum(), "unallocated_DAs": len(un)}
            row |= err_metrics(est, ref)
            rows.append(row)
        log(f"V6 r={r} done")
    t = pd.DataFrame(rows)
    t.to_csv(C.TABLES / "validation_V6_hierarchical.csv", index=False)
    return t


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-v6", action="store_true")
    args = ap.parse_args()
    C.TABLES.mkdir(exist_ok=True)
    log = Log(C.TABLES / "phaseE_log.txt")
    t1, t2, t3 = v1_v2_v3(log)
    t4 = v4(log)
    t5 = v5(log)
    summ = [
        {"id": "V1", "check": "DB-level conservation, method x r", "criterion": "max |eps(d)| < 1e-6",
         "result": f"max {t1.max_abs_eps.max():.1e} over {len(t1)} method x r layers", "pass": bool(t1['pass'].all())},
        {"id": "V2", "check": "Province conservation (Eq. 8)", "criterion": "|eps(p)| < 1e-6; national 36,991,971",
         "result": f"max |eps(p)| {t2.eps.abs().max():.1e}; national totals {sorted(set(t2.loc[t2.PR == 'Canada', 'layer_pop'].round(6)))}",
         "pass": bool(t2['pass'].all())},
        {"id": "V3", "check": "Cross-resolution invariance", "criterion": "exact (<= 1e-9)",
         "result": f"max DB total diff {t3.max_abs_diff_across_r.max():.1e}; s(d) identical", "pass": bool(t3['pass'].all())},
        {"id": "V4", "check": "Non-nesting (parent aggregation vs direct)", "criterion": "report",
         "result": "; ".join(f"{r.tag} {r.method} {r.from_res}->{r.to_res}: D/P {r.D_over_P_pct:.3f}%, >1 person {r.n_cells_diff_gt1:,}, max {r.max_abs_diff:.1f}"
                             for r in t4[t4.method == 'hyb'].itertuples()), "pass": np.nan},
        {"id": "V5", "check": "NAR fallback diagnostics", "criterion": "report; tier-3 = 0",
         "result": "; ".join(f"r{r.res}: tier1 {r.tier1_dbs:,}, tier2 {r.tier2_dbs:,}, tier3 {r.tier3_dbs}, NAR-only cells {r.nar_only_cells:,}, NAR cells <1 {r.nar_cells_lt1:,}"
                             for r in t5.itertuples()), "pass": bool(t5.pass_tier3_zero.all())},
    ]
    if not args.skip_v6:
        t6 = v6(log)
        summ.append({"id": "V6", "check": "Hierarchical accuracy (DA -> cells vs DB-based NAR)", "criterion": "report",
                     "result": "; ".join(f"r{r.res} {r.estimator}: MAE {r.MAE:.2f}, RMSE {r.RMSE:.1f}, MdAPE(M>=5) {r.median_APE_M5:.3f}, D/P {r.D_over_P_pct:.2f}%"
                                         for r in t6.itertuples()), "pass": np.nan})
    s = pd.DataFrame(summ)
    s.to_csv(C.TABLES / "validation_summary.csv", index=False)
    for row in s.to_dict("records"):
        flag = "PASS" if row["pass"] is True else "FAIL" if row["pass"] is False else "report"
        log(f"{row['id']} [{flag}] {row['check']}: {row['result']}")
    return 0 if s["pass"].dropna().all() else 1


if __name__ == "__main__":
    sys.exit(main())
