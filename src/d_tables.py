"""Phase D tables for GATE D.

  tables/ablation_res8.csv            D1: one row per run (v1, v1+M1, v1+M2, v2, v2 BU {1,2,4}, v2 + HYB-V)
  tables/tau_by_res.csv               D2: block shares at each tau, and D/P for HYB vs PHH and HYB vs NAR per tau x r (v2)
  tables/vintage_flag_summary.csv     M3: flagged DBs and population at each gamma, overlap with thin coverage (v2)
  tables/vintage_by_pr.csv, vintage_by_popctr.csv, vintage_by_cma.csv, vintage_toronto_contributors.csv
  tables/nar_bu_class_by_pr.csv       M1: NAR locations by BU class, nationally and by province
  tables/pip_unassigned_by_pr.csv     M2: NAR locations outside every DB, under each boundary file
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from hexpop import metrics as M  # noqa: E402
from hexpop.io import Log  # noqa: E402

TORONTO = {8: "882b9bc711fffff", 7: "872b9bc71ffffff", 6: "862b9bc77ffffff"}
TRACKED_DBS = ["35204565001", "35204004008", "35204004007"]
ABLATION = [("v1", "base", "v1 (preprint)"), ("v1_M1", "base", "v1 + M1 (BU {1,2})"),
            ("v1_M2", "base", "v1 + M2 (digital PIP)"), ("v2", "base", "v2 = v1 + M1 + M2"),
            ("v2", "bu124", "v2, BU {1,2,4}"), ("v2", "hybv", "v2 + HYB-V")]
POPCTR = {"1": "rural area", "2": "small population centre", "3": "medium population centre",
          "4": "large urban population centre"}
CMATYPE = {"B": "CMA", "D": "CA (tracted)", "K": "CA (non-tracted)", "G": "MIZ strong", "H": "MIZ moderate",
           "I": "MIZ weak", "J": "MIZ none"}


def cell_totals(st: C.RunSettings, r: int) -> pd.DataFrame:
    lt = pd.read_parquet(st.res_dir(r) / "contrib_long.parquet", columns=["DBUID", "h3", "pop_phh", "pop_nar", "pop_hyb"])
    return lt.groupby("h3")[["pop_phh", "pop_nar", "pop_hyb"]].sum()


def dp(a: pd.Series, b: pd.Series) -> float:
    return M.displaced(M.pair_frame(a, b))["D_over_P"]


def ablation(log: Log) -> pd.DataFrame:
    nar_pts = pd.read_parquet(C.NAR_POINTS, columns=["DBUID_carto", "DBUID_digital"])
    rows = []
    for method, variant, label in ABLATION:
        st = C.settings(method, variant)
        db = pd.read_parquet(st.out_dir / "db_table.parquet")
        P = db.POP.sum()
        pop_db = db.POP > 0
        cells = cell_totals(st, 8)
        s = db.s_final
        thin = pop_db & (db.n > 0) & (db.c > C.FINAL_TAU)
        rows.append({
            "run": label, "tag": st.tag,
            "nar_unassigned_pip": int(nar_pts[st.dbuid_col].isna().sum()),
            "nar_locations_used": int(db.n.sum()),
            "nar_locations_in_populated_dbs": int(db.n[pop_db].sum()),
            "zero_coverage_dbs": int(db.zero_cov.sum()),
            "zero_coverage_pct_pop": 100 * db.POP[db.zero_cov].sum() / P,
            "thin_coverage_dbs_tau50": int(thin.sum()),
            "thin_coverage_pct_pop_tau50": 100 * db.POP[thin].sum() / P,
            "phh_source_dbs_tau50": int((s == "PHH").sum()),
            "phh_source_pct_pop_tau50": 100 * db.POP[s == "PHH"].sum() / P,
            "vintage_flag_dbs_g1.5": int(db["vint_g1.5"].sum()),
            "DP_phh_vs_nar_pct": 100 * dp(cells.pop_phh, cells.pop_nar),
            "DP_hyb_vs_phh_pct": 100 * dp(cells.pop_phh, cells.pop_hyb),
            "DP_hyb_vs_nar_pct": 100 * dp(cells.pop_nar, cells.pop_hyb),
            "cells_nar": int((cells.pop_nar > 0).sum()),
            "cells_hyb": int((cells.pop_hyb > 0).sum()),
            f"{TORONTO[8]}_phh": cells.pop_phh.get(TORONTO[8], 0.0),
            f"{TORONTO[8]}_nar": cells.pop_nar.get(TORONTO[8], 0.0),
            f"{TORONTO[8]}_hyb": cells.pop_hyb.get(TORONTO[8], 0.0),
        })
        log(f"ablation: {label} done")
    t = pd.DataFrame(rows)
    t.to_csv(C.TABLES / "ablation_res8.csv", index=False)
    return t


def tau_by_res(log: Log) -> pd.DataFrame:
    st = C.settings("v2")
    db = pd.read_parquet(st.out_dir / "db_table.parquet").set_index("DBUID")
    P = db.POP.sum()
    sweep = pd.read_csv(st.out_dir / "tau_sweep.csv").set_index("tau_people_per_point")
    rows = []
    for r in C.RESOLUTIONS:
        lt = pd.read_parquet(st.res_dir(r) / "contrib_long.parquet", columns=["DBUID", "h3", "pop_phh", "pop_nar"])
        phh = lt.groupby("h3").pop_phh.sum()
        nar = lt.groupby("h3").pop_nar.sum()
        for tau in C.TAUS:
            src = lt.DBUID.map(db[f"s_tau{tau}"].astype(str)).fillna("n/a")
            hyb = pd.Series(np.where(src == "PHH", lt.pop_phh, np.where(src == "NAR", lt.pop_nar, 0.0))).groupby(lt.h3.to_numpy()).sum()
            s = db[f"s_tau{tau}"]
            rows.append({"res": r, "tau": tau,
                         "n_dbs_phh": int((s == "PHH").sum()), "pct_pop_phh": 100 * db.POP[s == "PHH"].sum() / P,
                         "n_dbs_zero_cov": int(sweep.loc[tau, "n_zero_coverage_dbs"]),
                         "n_dbs_thin": int(sweep.loc[tau, "n_thin_coverage_dbs"]),
                         "cells_hyb": int((hyb > 0).sum()),
                         "DP_hyb_vs_phh_pct": 100 * dp(phh, hyb), "DP_hyb_vs_nar_pct": 100 * dp(nar, hyb),
                         "DP_phh_vs_nar_pct": 100 * dp(phh, nar)})
        log(f"tau x r: r={r} done")
    t = pd.DataFrame(rows)
    t.to_csv(C.TABLES / "tau_by_res.csv", index=False)
    return t


def vintage(log: Log) -> None:
    st = C.settings("v2")
    db = pd.read_parquet(st.out_dir / "db_table.parquet")
    gaf = pd.read_csv(C.GAF_CSV, usecols=["DBUID_IDIDU", "CMATYPE_RMRGENRE"], dtype=str, encoding="latin1")
    db = db.merge(gaf.rename(columns={"DBUID_IDIDU": "DBUID", "CMATYPE_RMRGENRE": "CMATYPE"}), on="DBUID", how="left")
    P = db.POP.sum()
    f = db["vint_g1.5"]

    rows = []
    for gam in [C.VINTAGE_GAMMA] + C.VINTAGE_GAMMAS_SENS:
        g = db[f"vint_g{gam:g}"]
        row = {"gamma": gam, "n_flagged": int(g.sum()), "pop_flagged": db.POP[g].sum(),
               "pct_pop_flagged": 100 * db.POP[g].sum() / P,
               "a_flagged": int(db.a[g].sum()), "w_flagged": db.w[g].sum(),
               "excess_a_minus_w": (db.a - db.w)[g].sum(),
               "flagged_already_phh_tau50_base": int((g & (db.s_final == "PHH")).sum())}
        for tau in C.TAUS:
            thin = (db.POP > 0) & (db.n > 0) & (db.c > tau)
            row[f"flagged_and_thin_tau{tau}"] = int((g & thin).sum())
        rows.append(row)
    pd.DataFrame(rows).to_csv(C.TABLES / "vintage_flag_summary.csv", index=False)

    def by(col, labels=None):
        t = db.groupby(col).agg(n_dbs=("POP", lambda s: int((s > 0).sum())), pop=("POP", "sum"))
        t["n_flagged"] = f.groupby(db[col]).sum().astype(int)
        t["pop_flagged"] = db.POP[f].groupby(db[col][f]).sum()
        t = t.fillna(0)
        t["pct_dbs_flagged"] = 100 * t.n_flagged / t.n_dbs
        t["pct_pop_flagged"] = 100 * t.pop_flagged / t["pop"]
        t["share_of_all_flagged_pop"] = 100 * t.pop_flagged / db.POP[f].sum()
        if labels:
            t.index = [f"{i} {labels.get(str(i), '')}".strip() for i in t.index]
        return t

    by("PR").to_csv(C.TABLES / "vintage_by_pr.csv")
    pc = pd.concat([by("POPCTRRACLASS", POPCTR), by("CMATYPE", CMATYPE)], keys=["popctr_class", "cma_type"])
    pc.to_csv(C.TABLES / "vintage_by_popctr.csv")
    cma = by("CMANAME").sort_values("pop_flagged", ascending=False)
    cma.head(25).to_csv(C.TABLES / "vintage_by_cma.csv")

    lt = pd.read_parquet(st.res_dir(8) / "contrib_long.parquet", columns=["DBUID", "h3", "pop_phh", "pop_nar"])
    tor = lt[lt.h3 == TORONTO[8]].groupby("DBUID")[["pop_phh", "pop_nar"]].sum()
    cols = ["DBUID", "POP", "n", "c", "a", "w", "g", "vint_g1.5", "vint_g1.25", "vint_g2", "s_final"]
    tc = db.set_index("DBUID").loc[tor.index.union(TRACKED_DBS), cols[1:]].join(tor)
    tc["tracked"] = tc.index.isin(TRACKED_DBS)
    tc.sort_values("POP", ascending=False).to_csv(C.TABLES / "vintage_toronto_contributors.csv")
    log(f"vintage tables written; Toronto 882b9bc711fffff contributors: {len(tor)}, "
        f"flagged at gamma 1.5: {int(tc['vint_g1.5'].sum())}")

    shutil.copy(C.DATA_INT / "a4_nar_counts_by_pr.csv", C.TABLES / "nar_bu_class_by_pr.csv")
    shutil.copy(C.DATA_INT / "pip_unassigned_by_pr.csv", C.TABLES / "pip_unassigned_by_pr.csv")


def main() -> int:
    C.TABLES.mkdir(exist_ok=True)
    log = Log(C.TABLES / "phaseD_log.txt")
    ab = ablation(log)
    log("Ablation (r = 8):\n" + ab.T.to_string())
    tg = tau_by_res(log)
    log("tau x r (v2):\n" + tg.to_string(index=False))
    vintage(log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
