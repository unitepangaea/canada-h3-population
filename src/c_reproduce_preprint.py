"""Phase C: reproduce the preprint at r = 8 with METHOD_VERSION = v1 (GATE C).

Needs: run_all.py --method v1 --res 8 (output_v2/v1/res8/contrib_long.parquet, output_v2/v1/db_table.parquet).

Writes (tables/):
  phaseC_reproduction.csv     quantity, preprint, v1 rerun, match
  phaseC_table3.csv           Table 3 (fixed thresholds) rerun vs output/table3_corrected.csv
  phaseC_tau_sweep.csv        tau sweep rerun vs output/threshold_sweep_results.csv
  phaseC_hex_diff.csv         hexagon-by-hexagon differences against the preprint GPKGs
Accept: counts match exactly and each hexagon's population is within 0.01.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from hexpop import metrics as M  # noqa: E402
from hexpop.io import Log  # noqa: E402

HEX_TOL = 0.01
TORONTO = "882b9bc711fffff"

# Protocol Section 5 (preprint values). "exact" = must match exactly; otherwise compared at
# the precision printed in the preprint.
PREPRINT = [
    ("populated_dbs", 384_284, "exact"),
    ("national_population_P", 36_991_971, "exact"),
    ("phh_points", 16_614_053, "exact"),
    ("cells_union_phh_nar", 2_769_325, "exact"),
    ("cells_both_phh_nar", 266_657, "exact"),
    ("D", 3_162_153, "round0"),
    ("D_over_P_pct", 8.5, "round1"),
    ("pearson_r", 0.9954, "round4"),
    ("pearson_r_log1p", 0.9039, "round4"),
    ("spearman_rho", 0.8381, "round4"),
    ("ba_loa_halfwidth", 33.0, "round1"),
    ("zero_coverage_dbs", 31_375, "exact"),
    ("zero_coverage_pct_pop", 1.4, "round1"),
    ("tau50_phh_dbs", 35_741, "exact"),
    ("tau50_phh_pct_pop", 7.3, "round1"),
    (f"{TORONTO}_phh", 20_396.8, "round1"),
    (f"{TORONTO}_nar", 20_881.7, "round1"),
]


def matches(pre, val, how) -> bool:
    if how == "exact":
        return float(val) == float(pre)
    nd = int(how[-1])
    return round(float(val), nd) == round(float(pre), nd)


def main() -> int:
    st = C.settings("v1")
    rd = st.res_dir(8)
    C.TABLES.mkdir(exist_ok=True)
    log = Log(C.TABLES / "phaseC_log.txt")

    db = pd.read_parquet(st.out_dir / "db_table.parquet")
    lt = pd.read_parquet(rd / "contrib_long.parquet")
    cells = lt.groupby("h3")[["pop_phh", "pop_nar", "pop_hyb"]].sum()
    phh_n = len(pd.read_parquet(C.PHH_POINTS, columns=["pop"]))

    m = M.core_metrics(cells.pop_phh, cells.pop_nar)
    P = db.POP.sum()
    s = db.s_final
    val = {
        "populated_dbs": int((db.POP > 0).sum()),
        "national_population_P": P,
        "phh_points": phh_n,
        "cells_union_phh_nar": m["n_union"],
        "cells_both_phh_nar": m["n_both"],
        "D": m["D"],
        "D_over_P_pct": 100 * m["D_over_P"],
        "pearson_r": m["pearson_r"],
        "pearson_r_log1p": m["pearson_r_log1p"],
        "spearman_rho": m["spearman_rho"],
        "ba_loa_halfwidth": 1.96 * m["ba_sd"],
        "zero_coverage_dbs": int(db.zero_cov.sum()),
        "zero_coverage_pct_pop": 100 * db.POP[db.zero_cov].sum() / P,
        "tau50_phh_dbs": int((s == "PHH").sum()),
        "tau50_phh_pct_pop": 100 * db.POP[s == "PHH"].sum() / P,
        f"{TORONTO}_phh": cells.loc[TORONTO, "pop_phh"],
        f"{TORONTO}_nar": cells.loc[TORONTO, "pop_nar"],
    }
    rows = [{"quantity": q, "preprint": pre, "v1_rerun": val[q], "compare": how,
             "match": matches(pre, val[q], how)} for q, pre, how in PREPRINT]
    rep = pd.DataFrame(rows)
    extra = pd.DataFrame([{"quantity": k, "preprint": np.nan, "v1_rerun": v, "compare": "info", "match": np.nan}
                          for k, v in m.items() if k not in ("n_union", "n_both", "D", "pearson_r",
                                                              "pearson_r_log1p", "spearman_rho")]
                         + [{"quantity": f"{TORONTO}_hyb", "preprint": np.nan,
                             "v1_rerun": cells.loc[TORONTO, "pop_hyb"], "compare": "info", "match": np.nan}])
    rep = pd.concat([rep, extra], ignore_index=True)
    rep.to_csv(C.TABLES / "phaseC_reproduction.csv", index=False)
    log("Reproduction table:\n" + rep.to_string(index=False))

    # Table 3 and tau sweep against the preprint's corrected outputs
    t3 = M.table3_fixed(M.pair_frame(cells.pop_phh, cells.pop_nar))
    ref3 = pd.read_csv(C.PREPRINT_TABLE3_CSV)
    t3 = t3.merge(ref3, on="agreement", suffixes=("", "_preprint"))
    t3["n_match"] = t3.n_hexes == t3.n_hexes_preprint
    t3.to_csv(C.TABLES / "phaseC_table3.csv", index=False)
    log("Table 3 (fixed thresholds):\n" + t3.to_string(index=False))

    sw = pd.read_csv(st.out_dir / "tau_sweep.csv")
    refsw = pd.read_csv(C.PREPRINT_SWEEP_CSV)
    cols = list(refsw.columns)
    swc = sw[cols].merge(refsw, on="tau_people_per_point", suffixes=("", "_preprint"))
    swc["all_match"] = np.all([np.isclose(swc[c], swc[f"{c}_preprint"]) for c in cols[1:]], axis=0)
    swc.to_csv(C.TABLES / "phaseC_tau_sweep.csv", index=False)
    log(f"tau sweep matches the preprint at every tau: {bool(swc.all_match.all())}")

    # Hexagon by hexagon
    diffs = []
    ref = pyogrio.read_dataframe(C.PREPRINT_COMPARISON_GPKG, read_geometry=False, columns=["h3", "pop_phh", "pop_nar"])
    ref = ref.set_index("h3")
    for col in ("pop_phh", "pop_nar"):
        a = cells[col][cells[col] > 0]
        b = ref[col][ref[col] > 0]
        j = pd.concat({"rerun": a, "preprint": b}, axis=1).fillna(0.0)
        d = (j.rerun - j.preprint).abs()
        diffs.append({"layer": col, "reference": C.PREPRINT_COMPARISON_GPKG.name, "n_rerun": len(a),
                      "n_preprint": len(b), "only_rerun": int(((j.preprint == 0) & (j.rerun > 0)).sum()),
                      "only_preprint": int(((j.rerun == 0) & (j.preprint > 0)).sum()),
                      "max_abs_diff": d.max(), "n_over_tol": int((d > HEX_TOL).sum()),
                      "argmax": d.idxmax()})
    hyb = pyogrio.read_dataframe(C.PREPRINT_HYBRID_GPKG, read_geometry=False, columns=["h3", "population"]).set_index("h3")
    a = cells.pop_hyb[cells.pop_hyb > 0]
    b = hyb.population[hyb.population > 0]
    j = pd.concat({"rerun": a, "preprint": b}, axis=1).fillna(0.0)
    d = (j.rerun - j.preprint).abs()
    diffs.append({"layer": "pop_hyb", "reference": C.PREPRINT_HYBRID_GPKG.name, "n_rerun": len(a),
                  "n_preprint": len(b), "only_rerun": int(((j.preprint == 0) & (j.rerun > 0)).sum()),
                  "only_preprint": int(((j.rerun == 0) & (j.preprint > 0)).sum()),
                  "max_abs_diff": d.max(), "n_over_tol": int((d > HEX_TOL).sum()), "argmax": d.idxmax()})
    hd = pd.DataFrame(diffs)
    hd.to_csv(C.TABLES / "phaseC_hex_diff.csv", index=False)
    log("Hexagon-by-hexagon:\n" + hd.to_string(index=False))

    ok = bool(rep.loc[rep["compare"] != "info", "match"].all()) and bool((hd.n_over_tol == 0).all()) \
        and bool((hd.only_rerun == 0).all() and (hd.only_preprint == 0).all())
    log(f"ACCEPT C: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
