"""06: Phase F5 case studies.

Toronto: 882b9bc711fffff (r = 8) and its parents 872b9bc71ffffff (r = 7) and 862b9bc77ffffff (r = 6).
  Eq. 19: Δ(d, h) = POP_NAR(d, h) - POP_PHH(d, h); Eq. 20: G(h) = Σ_d |Δ(d, h)|, share(d, h) = |Δ(d, h)| / G(h).
  The v1 run at r = 8 is included as a check against the preprint (Δ = 484.8, G = 1,013.0).
  Tracked DBs 35204565001 (reallocation), 35204004008 (thin coverage) and 35204004007: contribution to the
  Toronto cell and the DB's own displacement D_d = ½ Σ_h |Δ(d, h)| over all cells, at each r.

National re-ranking (PHH vs NAR, v2): top 500 cells by |Δ| and by R (cells with M >= 5) at each r, labelled with
  the CSD and CMA/CA holding the largest share of the cell's population M (from the GAF codes of the contributing
  DBs). Each CMA/CA's share of the top-500 cells is compared with its share of national population.

Writes tables/F5_toronto_decomposition.csv, F5_toronto_summary.csv, F5_tracked_dbs.csv,
       F5_top500_cells.csv, F5_rerank_by_cma.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from hexpop.io import Log  # noqa: E402

TORONTO = {8: "882b9bc711fffff", 7: "872b9bc71ffffff", 6: "862b9bc77ffffff"}
TRACKED = {"35204565001": "reallocation", "35204004008": "thin coverage", "35204004007": "tracked"}
TOP = 500


def toronto(log: Log):
    dec, summ, tracked = [], [], []
    runs = [(C.settings("v2"), r) for r in C.RESOLUTIONS] + [(C.settings("v1"), 8)]
    for st, r in runs:
        db = pd.read_parquet(st.out_dir / "db_table.parquet", columns=["DBUID", "POP", "n", "c", "s_final"]).set_index("DBUID")
        lt = pd.read_parquet(st.res_dir(r) / "contrib_long.parquet", columns=["DBUID", "h3", "pop_phh", "pop_nar", "pop_hyb"])
        cell = TORONTO[r]
        t = lt[lt.h3 == cell].groupby("DBUID")[["pop_phh", "pop_nar", "pop_hyb"]].sum()
        t["delta"] = t.pop_nar - t.pop_phh
        G = t.delta.abs().sum()
        t["share_of_G_pct"] = 100 * t.delta.abs() / G
        t = t.join(db).sort_values("share_of_G_pct", ascending=False)
        t.insert(0, "tag", st.tag)
        t.insert(1, "res", r)
        t.insert(2, "h3", cell)
        dec.append(t.reset_index())
        top3 = t.share_of_G_pct.head(3).sum()
        summ.append({"tag": st.tag, "res": r, "h3": cell, "n_dbs": len(t), "PHH": t.pop_phh.sum(), "NAR": t.pop_nar.sum(),
                     "HYB": t.pop_hyb.sum(), "delta": t.delta.sum(), "G": G, "delta_over_G": t.delta.sum() / G,
                     "top3_share_of_G_pct": top3, "top3_dbs": ";".join(t.index[:3])})
        dd = lt.assign(ad=(lt.pop_nar - lt.pop_phh).abs())
        dd = dd[dd.DBUID.isin(list(TRACKED))].groupby("DBUID").ad.sum() / 2
        for d, role in TRACKED.items():
            tracked.append({"tag": st.tag, "res": r, "DBUID": d, "role": role, "POP": db.POP.get(d), "n": db.n.get(d),
                            "c": db.c.get(d), "s_final": db.s_final.get(d),
                            "delta_in_toronto_cell": t.delta.get(d, 0.0),
                            "share_of_G_pct": t.share_of_G_pct.get(d, 0.0),
                            "D_d_all_cells": dd.get(d, 0.0), "D_d_over_POP_pct": 100 * dd.get(d, 0.0) / db.POP.get(d)})
    pd.concat(dec).to_csv(C.TABLES / "F5_toronto_decomposition.csv", index=False)
    s = pd.DataFrame(summ)
    s.to_csv(C.TABLES / "F5_toronto_summary.csv", index=False)
    tr = pd.DataFrame(tracked)
    tr.to_csv(C.TABLES / "F5_tracked_dbs.csv", index=False)
    log("Toronto summary:\n" + s.round(2).to_string(index=False))
    log("Tracked DBs:\n" + tr.round(2).to_string(index=False))


def rerank(log: Log):
    st = C.settings("v2")
    db = pd.read_parquet(st.out_dir / "db_table.parquet",
                         columns=["DBUID", "POP", "PR", "CSDUID", "CSDNAME", "CMAPUID", "CMANAME"])
    gaf = pd.read_csv(C.GAF_CSV, usecols=["DBUID_IDIDU", "CMATYPE_RMRGENRE"], dtype=str, encoding="latin1")
    db = db.merge(gaf.rename(columns={"DBUID_IDIDU": "DBUID", "CMATYPE_RMRGENRE": "CMATYPE"}), on="DBUID", how="left")
    db["in_cma_ca"] = db.CMATYPE.isin(["B", "D", "K"])
    db["place"] = np.where(db.in_cma_ca, db.CMANAME, "Outside CMAs and CAs")
    P = db.POP.sum()
    place_pop = db.groupby("place").POP.sum()
    dbl = db.set_index("DBUID")
    cells_out, by_place = [], []
    for r in C.RESOLUTIONS:
        lt = pd.read_parquet(st.res_dir(r) / "contrib_long.parquet", columns=["DBUID", "h3", "pop_phh", "pop_nar"])
        cells = lt.groupby("h3")[["pop_phh", "pop_nar"]].sum()
        cells = cells[(cells.pop_phh > 0) | (cells.pop_nar > 0)]
        cells["delta"] = cells.pop_nar - cells.pop_phh
        cells["abs_delta"] = cells.delta.abs()
        cells["M"] = (cells.pop_phh + cells.pop_nar) / 2
        cells["R"] = cells.abs_delta / cells.M
        # label: the CSD and place holding the largest share of the cell's M
        lt["m"] = (lt.pop_phh + lt.pop_nar) / 2
        for key in ("CSDUID", "place"):
            lt[key] = lt.DBUID.map(dbl[key])
        for key in ("CSDUID", "place"):
            g = lt.groupby(["h3", key]).m.sum().reset_index().sort_values("m", ascending=False).drop_duplicates("h3")
            cells[key] = g.set_index("h3")[key].reindex(cells.index)
            cells[f"{key}_share_of_M"] = (g.set_index("h3").m / cells.M.reindex(g.h3).to_numpy()).reindex(cells.index)
        csdname = db.drop_duplicates("CSDUID").set_index("CSDUID").CSDNAME
        cells["CSDNAME"] = cells.CSDUID.map(csdname)
        for rank_by, sub in [("abs_delta", cells), ("R_M5", cells[cells.M >= 5])]:
            col = "abs_delta" if rank_by == "abs_delta" else "R"
            top = sub.sort_values([col, "abs_delta"], ascending=False).head(TOP).copy()
            top["rank"] = np.arange(1, len(top) + 1)
            cells_out.append(top.reset_index().assign(res=r, ranked_by=rank_by))
            cnt = top.place.value_counts()
            t = pd.DataFrame({"n_top_cells": cnt, "share_top_cells_pct": 100 * cnt / len(top),
                              "sum_abs_delta_top": top.groupby("place").abs_delta.sum()})
            t["share_top_abs_delta_pct"] = 100 * t.sum_abs_delta_top / top.abs_delta.sum()
            t["share_pop_pct"] = 100 * place_pop.reindex(t.index) / P
            t["ratio_cells_to_pop"] = t.share_top_cells_pct / t.share_pop_pct
            by_place.append(t.sort_values("n_top_cells", ascending=False).reset_index(names="place")
                            .assign(res=r, ranked_by=rank_by))
        log(f"re-ranking r={r} done")
    pd.concat(cells_out).to_csv(C.TABLES / "F5_top500_cells.csv", index=False)
    bp = pd.concat(by_place)
    bp.to_csv(C.TABLES / "F5_rerank_by_cma.csv", index=False)
    for (r, rb), g in bp.groupby(["res", "ranked_by"]):
        log(f"r={r}, ranked by {rb}: top places\n" + g.head(8)[["place", "n_top_cells", "share_top_cells_pct", "share_pop_pct",
                                                                 "ratio_cells_to_pop"]].round(2).to_string(index=False))


def main() -> int:
    C.TABLES.mkdir(exist_ok=True)
    log = Log(C.TABLES / "phaseF5_log.txt")
    toronto(log)
    rerank(log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
