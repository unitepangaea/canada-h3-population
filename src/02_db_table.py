"""02: one row per DB for a method version and variant (protocol B2).

Columns:
  DBUID, POP, PR, CSDUID, CSDNAME, CMAUID, CMAPUID, CMANAME, POPCTRRAPUID, POPCTRRANAME, POPCTRRACLASS,
  DAUID, DB_LANDAREA_KM2, DB_TDWELL
  n            NAR locations in the DB under the active boundary and BU filter      n(d)
  n_all        NAR locations in the DB under the active boundary, no BU filter
  c            POP / n (people per location; NaN when n = 0)                         c(d)
  a            residential address records (BU_USE 1 or 2) at the DB's locations     a(d)
  w            PHH 2021 total dwellings                                              w(d)
  g            a / w                                                                 g(d)
  vint_g{γ}    probable post-2021 growth: g > γ and a - w >= VINTAGE_MIN_EXCESS
  zero_cov     POP > 0 and n = 0
  s_tau{τ}     hybrid source at each τ ('PHH', 'NAR', 'n/a'); HYB-V reassigns vint_g1.5 DBs to PHH
  s_final      s_tau{FINAL_TAU}
  n_cells_phh_{r}, n_cells_nar_{r}, forced_{r}
               distinct cells holding the DB's PHH points (pop > 0) and active NAR locations;
               forced = both are a single cell and it is the same cell (F3)

s(d) depends only on POP(d) and n(d), so it is the same at every resolution (design rule 2).
Writes output_v2/<tag>/db_table.parquet, tau_sweep.csv, vintage_summary.csv, 02_db_table_log.txt.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from hexpop import core  # noqa: E402
from hexpop.io import Log, load_gaf, universe_dbuids  # noqa: E402


def gamma_tag(g: float) -> str:
    return f"vint_g{g:g}"


def build(st: C.RunSettings, log: Log) -> pd.DataFrame:
    universe = universe_dbuids()
    gaf = load_gaf()
    db = gaf[gaf.DBUID.isin(universe)].set_index("DBUID")
    log(f"[{st.tag}] DBs {len(db):,}; populated {int((db.POP > 0).sum()):,}; P = {db.POP.sum():,.0f}")

    cols = [st.dbuid_col, "bu_class", "n_addr_res"] + [f"h3_{r}" for r in C.RESOLUTIONS]
    nar = pd.read_parquet(C.NAR_POINTS, columns=cols).rename(columns={st.dbuid_col: "DBUID"})
    n_tot = len(nar)
    nar = nar[nar.DBUID.notna() & nar.DBUID.isin(db.index)]
    log(f"[{st.tag}] NAR locations {n_tot:,}; assigned to a universe DB under the {st.pip_boundary} file "
        f"{len(nar):,}")
    active = nar[nar.bu_class.isin(list(st.bu_keep))] if st.use_bu_filter else nar
    log(f"[{st.tag}] active NAR locations (BU filter {'on, keep ' + str(sorted(st.bu_keep)) if st.use_bu_filter else 'off'}): "
        f"{len(active):,}")

    db["n"] = active.groupby("DBUID").size().reindex(db.index).fillna(0).astype("int64")
    db["n_all"] = nar.groupby("DBUID").size().reindex(db.index).fillna(0).astype("int64")
    db["c"] = np.where(db.n > 0, db.POP / db.n.where(db.n > 0, 1), np.nan)
    db["a"] = nar.groupby("DBUID")["n_addr_res"].sum().reindex(db.index).fillna(0).astype("int64")

    phh = pd.read_parquet(C.PHH_POINTS, columns=["DBUID", "pop", "dwell_total"] + [f"h3_{r}" for r in C.RESOLUTIONS])
    phh = phh[phh.DBUID.isin(db.index)]
    db["w"] = phh.groupby("DBUID")["dwell_total"].sum().reindex(db.index).fillna(0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        db["g"] = db.a / db.w
    for gam in [C.VINTAGE_GAMMA] + C.VINTAGE_GAMMAS_SENS:
        db[gamma_tag(gam)] = (db.POP > 0) & (db.g > gam) & ((db.a - db.w) >= C.VINTAGE_MIN_EXCESS)

    db["zero_cov"] = (db.POP > 0) & (db.n == 0)
    vflag = db[gamma_tag(C.VINTAGE_GAMMA)]
    for tau in C.TAUS:
        s = core.source_assignment(db.POP, db.n, tau)
        if st.hyb_v:
            s[vflag] = "PHH"
        db[f"s_tau{tau}"] = s.astype("category")
    db["s_final"] = db[f"s_tau{C.FINAL_TAU}"]

    phh_pos = phh[phh["pop"] > 0]
    for r in C.RESOLUTIONS:
        hc = f"h3_{r}"
        gp = phh_pos.groupby("DBUID")[hc].agg(["nunique", "min"])
        gn = active.groupby("DBUID")[hc].agg(["nunique", "min"])
        db[f"n_cells_phh_{r}"] = gp["nunique"].reindex(db.index).fillna(0).astype("int32")
        db[f"n_cells_nar_{r}"] = gn["nunique"].reindex(db.index).fillna(0).astype("int32")
        same = gp["min"].reindex(db.index) == gn["min"].reindex(db.index)
        db[f"forced_{r}"] = (db[f"n_cells_phh_{r}"] == 1) & (db[f"n_cells_nar_{r}"] == 1) & same.fillna(False)
    return db.reset_index()


def summarise(db: pd.DataFrame, st: C.RunSettings, log: Log) -> None:
    out = st.out_dir
    pop = db.set_index("DBUID").POP
    sweep = core.tau_sweep(pop, db.set_index("DBUID").n, C.TAUS)
    if st.hyb_v:
        for i, tau in enumerate(C.TAUS):
            s = db[f"s_tau{tau}"]
            sweep.loc[i, "n_dbs_phh_hybv"] = int((s == "PHH").sum())
            sweep.loc[i, "pct_pop_phh_hybv"] = round(100 * db.POP[s == "PHH"].sum() / db.POP.sum(), 3)
    sweep.to_csv(out / "tau_sweep.csv", index=False)
    log(f"[{st.tag}] tau sweep:\n" + sweep.to_string(index=False))

    P = db.POP.sum()
    rows = []
    for gam in [C.VINTAGE_GAMMA] + C.VINTAGE_GAMMAS_SENS:
        f = db[gamma_tag(gam)]
        row = {"gamma": gam, "n_flagged": int(f.sum()), "pop_flagged": db.POP[f].sum(),
               "pct_pop_flagged": round(100 * db.POP[f].sum() / P, 3)}
        for tau in C.TAUS:
            thin = (db.POP > 0) & (db.n > 0) & (db.c > tau)
            row[f"n_flagged_and_thin_tau{tau}"] = int((f & thin).sum())
        rows.append(row)
    vs = pd.DataFrame(rows)
    vs.to_csv(out / "vintage_summary.csv", index=False)
    log(f"[{st.tag}] vintage flag summary:\n" + vs.to_string(index=False))

    zc = db.zero_cov
    s = db.s_final
    log(f"[{st.tag}] zero-coverage DBs {int(zc.sum()):,} ({100 * db.POP[zc].sum() / P:.2f}% of population); "
        f"tau={C.FINAL_TAU}: PHH-allocated DBs {int((s == 'PHH').sum()):,} ({100 * db.POP[s == 'PHH'].sum() / P:.2f}% of population)")
    for r in C.RESOLUTIONS:
        f = db[f"forced_{r}"] & (db.POP > 0)
        log(f"[{st.tag}] r={r}: forced DBs {int(f.sum()):,} ({100 * db.POP[f].sum() / P:.2f}% of population)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--method", default=C.METHOD_VERSION, choices=list(C.METHODS))
    ap.add_argument("--variant", default="base", choices=C.VARIANTS)
    args = ap.parse_args()
    st = C.settings(args.method, args.variant)
    st.out_dir.mkdir(parents=True, exist_ok=True)
    log = Log(st.out_dir / "02_db_table_log.txt")
    db = build(st, log)
    db.to_parquet(st.out_dir / "db_table.parquet", index=False)
    log(f"Wrote {C.rel(st.out_dir / 'db_table.parquet')} ({len(db):,} rows)")
    summarise(db, st, log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
