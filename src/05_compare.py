"""05: Phase F cross-resolution comparison (F1 to F4, F6 to F8) for the headline v2 layers.

Pairs (x, y), Δ(h) = y(h) - x(h), M(h) = (x + y) / 2, R(h) = |Δ(h)| / M(h)  (preprint Eqs. 13 to 18):
  PHH vs NAR  (x = PHH, y = NAR)    HYB vs PHH  (x = PHH, y = HYB)    HYB vs NAR  (x = NAR, y = HYB)

Writes tables/:
  F1_core_metrics.csv          |H|, |H∩|, D, D/P, r, r_log, rho, Bland-Altman, MARD (all, M >= 5); pair x r (+ HYB-V rows)
  F2_categories_fixed.csv      preprint thresholds (5, 25, 100) on H
  F2_categories_relative.csv   R(h) categories on cells with M >= 5; x-only and y-only reported separately
  F3_forced.csv                forced DBs and population by r; D / population in non-forced DBs
  F3_by_n_dbs.csv              agreement by n_dbs_contributing (cells)
  F3_by_area_ratio.csv         DB-level displacement by DB land area / mean cell area
  F4_decomposition.csv         D_8 = L(8->7) + L(7->6) + D_6^agg on parent-aggregated layers
  F4_by_db_class.csv           DB-level analogue by DB class (zero coverage, thin at tau = 50, other)
  F6_by_province.csv, F6_by_popctr.csv   D/P on stratum-restricted layers, pair x r
  F7_disclosure.csv            share of populated cells (and population) with population < 5, < 10, < 50
  F8_descriptives.csv          populated cells, quantiles of population and density, populated area share
"""
from __future__ import annotations

import sys
from pathlib import Path

import h3
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from hexpop import metrics as M  # noqa: E402
from hexpop.io import Log  # noqa: E402

PAIRS = [("PHH vs NAR", "pop_phh", "pop_nar"), ("HYB vs PHH", "pop_phh", "pop_hyb"), ("HYB vs NAR", "pop_nar", "pop_hyb")]
SHORT = {"pop_phh": "PHH", "pop_nar": "NAR", "pop_hyb": "HYB"}
ST = C.settings("v2")
POPCTR = {"1": "rural area", "2": "small population centre", "3": "medium population centre",
          "4": "large urban population centre"}


def load(r: int, st=ST) -> pd.DataFrame:
    return pd.read_parquet(st.res_dir(r) / "contrib_long.parquet", columns=["DBUID", "h3", "pop_phh", "pop_nar", "pop_hyb"])


def cells_of(lt: pd.DataFrame) -> pd.DataFrame:
    return lt.groupby("h3")[["pop_phh", "pop_nar", "pop_hyb"]].sum()


# ----------------------------------------------------------------------------- F1, F2
def f1_f2(lts: dict, log: Log):
    f1, fx, rel = [], [], []
    hybv = {r: cells_of(load(r, C.settings("v2", "hybv"))) for r in C.RESOLUTIONS}
    for r in C.RESOLUTIONS:
        cells = cells_of(lts[r])
        for name, x, y in PAIRS:
            f1.append({"tag": "v2", "pair": name, "res": r} | M.core_metrics(cells[x], cells[y]))
            df = M.pair_frame(cells[x], cells[y])
            t = M.table3_fixed(df)
            t["agreement"] = t.agreement.replace({"nar_only": f"{SHORT[y]}-only", "phh_only": f"{SHORT[x]}-only"})
            fx.append(t.assign(pair=name, res=r))
            rel.append(relative_categories(df, SHORT[x], SHORT[y]).assign(pair=name, res=r))
        for name, x in [("HYB-V vs PHH", "pop_phh"), ("HYB-V vs NAR", "pop_nar")]:
            f1.append({"tag": "v2_hybv", "pair": name, "res": r} | M.core_metrics(cells[x], hybv[r].pop_hyb))
        log(f"F1/F2 r={r} done")
    f1 = pd.DataFrame(f1)
    f1.to_csv(C.TABLES / "F1_core_metrics.csv", index=False)
    pd.concat(fx).to_csv(C.TABLES / "F2_categories_fixed.csv", index=False)
    pd.concat(rel).to_csv(C.TABLES / "F2_categories_relative.csv", index=False)
    return f1


def relative_categories(df: pd.DataFrame, xs: str, ys: str) -> pd.DataFrame:
    """R(h) categories on H5 = {h in H: M(h) >= 5}. Denominators: |H5| for cells, sum of M over H5 for population.

    Coverage of H5 (share of H and of P) is returned in the 'H5' rows.
    """
    m = (df.x + df.y) / 2
    h5 = df[m >= 5]
    m5 = m[m >= 5]
    R = (h5.y - h5.x).abs() / m5
    cat = np.select([h5.x == 0, h5.y == 0, R < 0.05, R < 0.25, R < 0.50],
                    [f"{ys}-only", f"{xs}-only", "match", "minor", "moderate"], default="major")
    t = pd.DataFrame({"category": cat, "M": m5}).groupby("category").agg(n_cells=("M", "size"), pop_M=("M", "sum"))
    t["pct_of_cells_M5"] = 100 * t.n_cells / len(h5)
    t["pct_of_pop_M5"] = 100 * t.pop_M / m5.sum()
    t = t.reset_index()
    cover = pd.DataFrame([{"category": "H5 (M >= 5), coverage", "n_cells": len(h5), "pop_M": m5.sum(),
                           "pct_of_cells_M5": 100 * len(h5) / len(df), "pct_of_pop_M5": 100 * m5.sum() / m.sum()}])
    order = ["match", "minor", "moderate", "major", f"{xs}-only", f"{ys}-only"]
    t["o"] = t.category.map({c: i for i, c in enumerate(order)})
    return pd.concat([t.sort_values("o").drop(columns="o"), cover], ignore_index=True)


# ----------------------------------------------------------------------------- F3
def f3(lts: dict, db: pd.DataFrame, log: Log):
    P = db.POP.sum()
    pop_db = db.POP > 0
    rows, by_n, by_area = [], [], []
    for r in C.RESOLUTIONS:
        lt = lts[r]
        cells = cells_of(lt)
        D = M.displaced(M.pair_frame(cells.pop_phh, cells.pop_nar))["D"]
        f = db[f"forced_{r}"] & pop_db
        # contribution-based definition (also covers zero-coverage DBs placed by the fallback)
        nz_p = lt[lt.pop_phh > 0].groupby("DBUID").h3.agg(["nunique", "min"])
        nz_n = lt[lt.pop_nar > 0].groupby("DBUID").h3.agg(["nunique", "min"])
        j = nz_p.add_suffix("_p").join(nz_n.add_suffix("_n"), how="inner")
        fc_ids = j.index[(j.nunique_p == 1) & (j.nunique_n == 1) & (j.min_p == j.min_n)]
        fc = db.DBUID.isin(fc_ids) & pop_db
        rows.append({"res": r, "populated_dbs": int(pop_db.sum()),
                     "forced_dbs": int(f.sum()), "pct_dbs_forced": 100 * f.sum() / pop_db.sum(),
                     "pct_pop_forced": 100 * db.POP[f].sum() / P,
                     "pop_non_forced": db.POP[pop_db & ~f].sum(),
                     "D_phh_vs_nar": D, "D_over_P_pct": 100 * D / P,
                     "D_over_pop_non_forced_pct": 100 * D / db.POP[pop_db & ~f].sum(),
                     "forced_dbs_contrib_def": int(fc.sum()), "pct_pop_forced_contrib_def": 100 * db.POP[fc].sum() / P,
                     "D_over_pop_non_forced_contrib_def_pct": 100 * D / db.POP[pop_db & ~fc].sum()})

        # cells by number of contributing DBs (to either layer)
        nd = lt[(lt.pop_phh > 0) | (lt.pop_nar > 0)].groupby("h3").DBUID.nunique()
        df = M.pair_frame(cells.pop_phh, cells.pop_nar)
        df["n_dbs"] = nd.reindex(df.index).fillna(0)
        df["bin"] = pd.cut(df.n_dbs, [0, 1, 2, 5, 10, 20, np.inf], labels=["1", "2", "3-5", "6-10", "11-20", "21+"])
        df["m"] = (df.x + df.y) / 2
        df["ad"] = (df.y - df.x).abs()
        g = df.groupby("bin", observed=True)
        t = pd.DataFrame({"n_cells": g.size(), "pop_M": g.m.sum(), "D_stratum": g.ad.sum() / 2})
        t["pct_cells"] = 100 * t.n_cells / len(df)
        t["pct_pop"] = 100 * t.pop_M / df.m.sum()
        t["share_of_D_pct"] = 100 * t.D_stratum / (df.ad.sum() / 2)
        t["D_over_M_pct"] = 100 * t.D_stratum / t.pop_M
        t["mard_M5"] = df[df.m >= 5].assign(R=lambda d: d.ad / d.m).groupby("bin", observed=True).R.median()
        by_n.append(t.reset_index().assign(res=r))

        # DB-level displacement by DB land area / mean cell area
        dd = lt.assign(ad=(lt.pop_nar - lt.pop_phh).abs()).groupby("DBUID").ad.sum() / 2
        d2 = db[pop_db].set_index("DBUID")[["POP", "DB_LANDAREA_KM2", f"forced_{r}"]].copy()
        d2["D_d"] = dd.reindex(d2.index).fillna(0)
        d2["ratio"] = d2.DB_LANDAREA_KM2 / h3.average_hexagon_area(r, "km^2")
        d2["bin"] = pd.cut(d2.ratio, [0, 0.01, 0.1, 1, 10, np.inf], right=False,
                           labels=["<0.01", "0.01-0.1", "0.1-1", "1-10", ">=10"])
        g = d2.groupby("bin", observed=True)
        t = pd.DataFrame({"n_dbs": g.size(), "pop": g.POP.sum(), "sum_D_d": g.D_d.sum(),
                          "pct_forced_dbs": 100 * g[f"forced_{r}"].mean()})
        t["pct_pop"] = 100 * t["pop"] / P
        t["D_d_over_pop_pct"] = 100 * t.sum_D_d / t["pop"]
        by_area.append(t.reset_index().assign(res=r, sum_D_d_all=d2.D_d.sum(), D_cells=D))
    t = pd.DataFrame(rows)
    t.to_csv(C.TABLES / "F3_forced.csv", index=False)
    pd.concat(by_n).to_csv(C.TABLES / "F3_by_n_dbs.csv", index=False)
    pd.concat(by_area).to_csv(C.TABLES / "F3_by_area_ratio.csv", index=False)
    log("F3 done")
    return t


# ----------------------------------------------------------------------------- F4
def parents(cells_str: np.ndarray, res: int) -> np.ndarray:
    u, inv = np.unique(cells_str, return_inverse=True)
    return np.array([h3.cell_to_parent(c, res) for c in u])[inv]


def f4(lts: dict, db: pd.DataFrame, log: Log):
    rows, cls_rows = [], []
    lt8 = lts[8]
    p7 = parents(lt8.h3.to_numpy(), 7)
    p6 = parents(p7, 6)
    cells8 = cells_of(lt8)
    direct = {r: cells_of(lts[r]) for r in (7, 6)}
    zc = set(db.DBUID[db.zero_cov])
    thin = set(db.DBUID[(db.POP > 0) & (db.n > 0) & (db.c > C.FINAL_TAU)])
    populated = set(db.DBUID[db.POP > 0])
    cls = np.where(lt8.DBUID.isin(zc), "zero coverage", np.where(lt8.DBUID.isin(thin), "thin (tau = 50)", "other"))
    for name, x, y in PAIRS:
        d8 = lt8[y] - lt8[x]
        D8_cell = cells8[y] - cells8[x]
        D8 = 0.5 * D8_cell.abs().sum()
        cell_p7 = pd.Series(parents(D8_cell.index.to_numpy(), 7), index=D8_cell.index)
        d7 = D8_cell.groupby(cell_p7.to_numpy()).sum()
        L87 = 0.5 * (D8_cell.abs().groupby(cell_p7.to_numpy()).sum() - d7.abs()).sum()
        D7agg = 0.5 * d7.abs().sum()
        p76 = pd.Series(parents(d7.index.to_numpy(), 6), index=d7.index)
        d6 = d7.groupby(p76.to_numpy()).sum()
        L76 = 0.5 * (d7.abs().groupby(p76.to_numpy()).sum() - d6.abs()).sum()
        D6agg = 0.5 * d6.abs().sum()
        D7dir = 0.5 * (direct[7][y] - direct[7][x]).abs().sum()
        D6dir = 0.5 * (direct[6][y] - direct[6][x]).abs().sum()
        assert abs(D8 - (L87 + L76 + D6agg)) < 1e-6 * D8
        rows.append({"pair": name, "D8": D8, "L_8to7": L87, "D7_agg": D7agg, "L_7to6": L76, "D6_agg": D6agg,
                     "pct_local_resolves_within_res7_parent": 100 * L87 / D8,
                     "pct_persists_to_res7_resolves_within_res6": 100 * L76 / D8,
                     "pct_persists_to_res6": 100 * D6agg / D8,
                     "D7_direct": D7dir, "D6_direct": D6dir,
                     "identity_residual": D8 - (L87 + L76 + D6agg)})
        # DB-level analogue: sum over DBs of each DB's own displacement at 8, 7agg, 6agg, by DB class
        f = pd.DataFrame({"DBUID": lt8.DBUID.to_numpy(), "cls": cls, "h8": lt8.h3.to_numpy(), "p7": p7, "p6": p6, "d": d8.to_numpy()})
        for c, g in f.groupby("cls"):
            s8 = 0.5 * g.d.abs().sum()
            s7 = 0.5 * g.groupby(["DBUID", "p7"]).d.sum().abs().sum()
            s6 = 0.5 * g.groupby(["DBUID", "p6"]).d.sum().abs().sum()
            cls_rows.append({"pair": name, "db_class": c, "n_populated_dbs": int(g.DBUID[g.DBUID.isin(populated)].nunique()),
                             "sum_D_d_res8": s8,
                             "sum_D_d_res7agg": s7, "sum_D_d_res6agg": s6,
                             "pct_local_8to7": 100 * (s8 - s7) / s8 if s8 else np.nan,
                             "pct_7to6": 100 * (s7 - s6) / s8 if s8 else np.nan,
                             "pct_persists_to_6": 100 * s6 / s8 if s8 else np.nan})
    t = pd.DataFrame(rows)
    t.to_csv(C.TABLES / "F4_decomposition.csv", index=False)
    tc = pd.DataFrame(cls_rows)
    tc["share_of_pair_DB_displacement_res8_pct"] = 100 * tc.sum_D_d_res8 / tc.groupby("pair").sum_D_d_res8.transform("sum")
    tc.to_csv(C.TABLES / "F4_by_db_class.csv", index=False)
    log("F4 done")
    return t, tc


# ----------------------------------------------------------------------------- F6
def f6(lts: dict, db: pd.DataFrame, log: Log):
    out = {}
    for col, fname, labels in [("PR", "F6_by_province.csv", None), ("POPCTRRACLASS", "F6_by_popctr.csv", POPCTR)]:
        key = db.set_index("DBUID")[col]
        popk = db.groupby(col).POP.sum()
        rows = []
        for r in C.RESOLUTIONS:
            lt = lts[r].copy()
            lt["k"] = lt.DBUID.map(key)
            for name, x, y in PAIRS:
                dk = (lt[y] - lt[x]).groupby([lt.k, lt.h3]).sum().abs().groupby(level=0).sum() / 2
                for k, v in dk.items():
                    rows.append({"stratum": f"{k} {labels[k]}" if labels else k, "res": r, "pair": name,
                                 "D": v, "P": popk[k], "D_over_P_pct": 100 * v / popk[k]})
        t = pd.DataFrame(rows)
        t.to_csv(C.TABLES / fname, index=False)
        out[col] = t
    log("F6 done")
    return out


# ----------------------------------------------------------------------------- F7, F8
def f7_f8(db: pd.DataFrame, log: Log):
    land = db.DB_LANDAREA_KM2.sum()
    f7, f8 = [], []
    for r in C.RESOLUTIONS:
        for m in ("phh", "nar", "hyb"):
            t = pd.read_parquet(ST.res_dir(r) / f"{m}_h3_res{r}.parquet", columns=["population", "area_km2", "pop_density_km2"])
            P = t.population.sum()
            row = {"res": r, "layer": m.upper(), "populated_cells": len(t)}
            for k in (5, 10, 50):
                s = t.population < k
                row[f"pct_cells_lt{k}"] = 100 * s.mean()
                row[f"pct_pop_in_cells_lt{k}"] = 100 * t.population[s].sum() / P
            f7.append(row)
            q = [0.01, 0.10, 0.25, 0.50, 0.75, 0.90, 0.99]
            d = {"res": r, "layer": m.upper(), "populated_cells": len(t), "mean_pop": t.population.mean()}
            d |= {f"pop_p{int(p * 100)}": v for p, v in t.population.quantile(q).items()}
            d["pop_max"] = t.population.max()
            d |= {f"density_p{int(p * 100)}": v for p, v in t.pop_density_km2.quantile(q).items()}
            d["density_max"] = t.pop_density_km2.max()
            d["populated_area_km2"] = t.area_km2.sum()
            d["pct_of_land_area"] = 100 * t.area_km2.sum() / land
            f8.append(d)
    a, b = pd.DataFrame(f7), pd.DataFrame(f8)
    a.to_csv(C.TABLES / "F7_disclosure.csv", index=False)
    b.to_csv(C.TABLES / "F8_descriptives.csv", index=False)
    log(f"F7/F8 done (land area {land:,.0f} km2)")
    return a, b


def main() -> int:
    C.TABLES.mkdir(exist_ok=True)
    log = Log(C.TABLES / "phaseF_log.txt")
    db = pd.read_parquet(ST.out_dir / "db_table.parquet")
    lts = {r: load(r) for r in C.RESOLUTIONS}
    f1 = f1_f2(lts, log)
    cols = ["pair", "res", "n_union", "n_both", "D", "D_over_P", "pearson_r", "pearson_r_log1p", "spearman_rho",
            "ba_sd", "ba_loa_upper", "mard_min0", "mard_min5"]
    log("F1:\n" + f1[f1.tag == "v2"][cols].round(4).to_string(index=False))
    t3 = f3(lts, db, log)
    log("F3:\n" + t3.round(3).to_string(index=False))
    t4, t4c = f4(lts, db, log)
    log("F4:\n" + t4.round(2).T.to_string())
    log("F4 by DB class:\n" + t4c.round(2).to_string(index=False))
    f6(lts, db, log)
    a, b = f7_f8(db, log)
    log("F7:\n" + a.round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
