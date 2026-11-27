"""08: Phase G manuscript tables and paper_values_v2.md (protocol Section 9).

Reads only files written by earlier phases (tables/*.csv, output_v2/v2/*); no number is typed in here.
Mean cell area and edge length come from h3 (v4) at run time.

Writes tables/manuscript/:
  T1_study_area.csv              Table 1 updated (resolutions, PHH points, NAR locations by BU class)
  T2_data_sources.csv            Table 2 updated (adds the NAR Addresses file and the digital DB boundary file)
  T_resolution_spec.csv          new resolution-specification table
  T3_relative_by_res.csv         Table 3 per r, relative categories, PHH vs NAR
  T3_relative_all_pairs.csv      supplement: relative categories, all three pairs
  T3_fixed_by_res.csv            supplement: preprint (fixed-threshold) categories per r, PHH vs NAR
  T4_hybrid_summary.csv          Table 4 under v2
  T5_tau_sensitivity.csv         Table 5 under v2, with D/P (HYB vs NAR) at each r
  T_ablation.csv                 new ablation table (r = 8)
  T_multires_summary.csv         new multi-resolution summary (F1, F3, F7)
  T_decomposition.csv            D8 decomposition by pair (F4)
  TS_province_by_res.csv         supplement: province x r D/P, three pairs
  tables_v2.md                   all of the above, formatted
and paper_values_v2.md (BASE): every number for the manuscript, with its source file.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import h3
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from hexpop.io import Log  # noqa: E402

OUT = C.TABLES / "manuscript"
T = C.TABLES
V2 = C.OUTPUT_V2 / "v2"
PR_NAMES = {"10": "Newfoundland and Labrador", "11": "Prince Edward Island", "12": "Nova Scotia",
            "13": "New Brunswick", "24": "Quebec", "35": "Ontario", "46": "Manitoba", "47": "Saskatchewan",
            "48": "Alberta", "59": "British Columbia", "60": "Yukon", "61": "Northwest Territories",
            "62": "Nunavut"}
PAIRS = ["PHH vs NAR", "HYB vs PHH", "HYB vs NAR"]
RS = C.RESOLUTIONS

PV: list[dict] = []


H3_SRC = f"h3 {h3.__version__} (average_hexagon_area / average_hexagon_edge_length)"


def rel(p) -> str:
    return p if isinstance(p, str) else C.rel(p)


def pv(key: str, raw, text: str, src, desc: str) -> str:
    srcs = src if isinstance(src, (list, tuple)) else [src]
    PV.append({"key": key, "value": text, "raw": raw, "source": "; ".join(rel(s) for s in srcs), "description": desc})
    return text


def n0(x) -> str:
    return f"{x:,.0f}"


def p1(x) -> str:
    return f"{x:.1f}%"


def p2(x) -> str:
    return f"{x:.2f}%"


def area(r: int) -> float:
    return h3.average_hexagon_area(r, unit="km^2")


def edge(r: int) -> float:
    return h3.average_hexagon_edge_length(r, unit="km")


def summary(r: int) -> dict:
    return json.loads((V2 / f"res{r}" / "allocate_summary.json").read_text())


# ----------------------------------------------------------------------------
def t1(db: pd.DataFrame) -> pd.DataFrame:
    phh = pd.read_parquet(C.PHH_POINTS, columns=["in_universe"])
    bu = pd.read_csv(T / "nar_bu_class_by_pr.csv", dtype={"pr": str}).set_index("pr").loc["Canada"]
    src_bu = T / "nar_bu_class_by_pr.csv"
    P = db.POP.sum()
    pop_dbs = int((db.POP > 0).sum())
    rows = [
        ("Provinces and territories covered", pv("n_pr", db.PR.nunique(), f"{db.PR.nunique()} (all of Canada)",
                                                  V2 / "db_table.parquet", "provinces and territories")),
        ("DBs with non-zero 2021 population", pv("populated_dbs", pop_dbs, n0(pop_dbs), V2 / "db_table.parquet",
                                                 "populated DBs in the universe")),
        ("Total population represented (P)", pv("P", P, n0(P), V2 / "db_table.parquet", "national population P")),
        ("H3 resolutions", "; ".join(f"{r} ({area(r):.2f} km²)" if r == 8 else f"{r} ({area(r):.1f} km²)"
                                     for r in RS)),
        ("PHH representative points processed", pv("phh_points", len(phh), n0(len(phh)), C.PHH_POINTS,
                                                   "PHH points in the 2021 release")),
        ("PHH points inside the DB universe", pv("phh_points_universe", int(phh.in_universe.sum()),
                                                 n0(phh.in_universe.sum()), C.PHH_POINTS,
                                                 "PHH points whose DB has a cartographic polygon")),
        ("NAR building locations (all)", pv("nar_locations_all", int(bu["Canada"]), n0(bu["Canada"]), src_bu,
                                            "NAR locations, all BU classes")),
        ("  of which BU class 1 (residential)", pv("nar_bu1", int(bu["1"]), n0(bu["1"]), src_bu, "BU class 1")),
        ("  of which BU class 2 (partly residential)", pv("nar_bu2", int(bu["2"]), n0(bu["2"]), src_bu, "BU class 2")),
        ("  of which BU class 3 (non-residential)", pv("nar_bu3", int(bu["3"]), n0(bu["3"]), src_bu, "BU class 3")),
        ("  of which BU class 4 (unknown)", pv("nar_bu4", int(bu["4"]), n0(bu["4"]), src_bu, "BU class 4")),
        ("NAR locations used (BU {1, 2})", pv("nar_used", int(db.n.sum()), n0(db.n.sum()), V2 / "db_table.parquet",
                                              "NAR locations kept by the residential filter and placed in a DB")),
        ("NAR address records (all / residential)",
         pv("nar_addr_all_res", (bu["addr_total"], bu["addr_res"]), f"{n0(bu['addr_total'])} / {n0(bu['addr_res'])}",
            src_bu, "NAR address records, all and residential")),
    ]
    return pd.DataFrame(rows, columns=["Quantity", "Value"])


def t2() -> pd.DataFrame:
    rows = [
        ("2021 Census Dissemination Block boundaries, cartographic (ldb_000b21a_e)", "Statistics Canada",
         "DB universe; areal fallback (tier 1)"),
        ("2021 Census Dissemination Block boundaries, digital (ldb_000a21a_e)", "Statistics Canada",
         "Point-in-polygon assignment of NAR locations (M2)"),
        ("2021 Geographic Attribute File", "Statistics Canada", "Authoritative population per block (DBPOP2021)"),
        ("Pseudo-Household Demographic Distribution, 2021", "Innovation, Science and Economic Development Canada",
         "Road-based dasymetric proxy"),
        ("National Address Register, Locations file (NAR-202606)", "Statistics Canada",
         "Address-based dasymetric proxy (building representative points)"),
        ("National Address Register, Addresses file (NAR-202606), BU_USE", "Statistics Canada",
         "Residential filter (M1) and residential address counts for the vintage check (M3)"),
    ]
    return pd.DataFrame(rows, columns=["Dataset", "Publisher", "Role"])


def t_res() -> pd.DataFrame:
    f7 = pd.read_csv(T / "F7_disclosure.csv")
    f8 = pd.read_csv(T / "F8_descriptives.csv")
    rows = []
    for r in RS:
        a, e = area(r), edge(r)
        pv(f"area_r{r}", a, f"{a:.3f}", H3_SRC, f"mean cell area at r={r} (km², h3 v4)")
        pv(f"edge_r{r}", e, f"{e:.3f}", H3_SRC, f"mean edge length at r={r} (km, h3 v4)")
        row = {"r": r, "Mean cell area (km²)": f"{a:.3f}", "Mean edge length (km)": f"{e:.3f}"}
        for lay in ["PHH", "NAR", "HYB"]:
            v = f8[(f8.res == r) & (f8.layer == lay)].iloc[0]
            row[f"Populated cells, {lay}"] = pv(f"cells_{lay.lower()}_r{r}", int(v.populated_cells),
                                                n0(v.populated_cells), T / "F8_descriptives.csv",
                                                f"populated {lay} cells at r={r}")
        h = f8[(f8.res == r) & (f8.layer == "HYB")].iloc[0]
        d = f7[(f7.res == r) & (f7.layer == "HYB")].iloc[0]
        row["HYB median population per populated cell"] = pv(f"hyb_median_pop_r{r}", h.pop_p50, f"{h.pop_p50:,.1f}",
                                                             T / "F8_descriptives.csv", f"HYB median cell pop r={r}")
        row["HYB populated area (km²)"] = pv(f"hyb_area_r{r}", h.populated_area_km2, n0(h.populated_area_km2),
                                            T / "F8_descriptives.csv", f"HYB populated area r={r}")
        row["HYB populated area (% of land)"] = pv(f"hyb_area_pct_r{r}", h.pct_of_land_area, p1(h.pct_of_land_area),
                                                  T / "F8_descriptives.csv", f"HYB populated area % of land r={r}")
        row["HYB cells < 5 people (%)"] = pv(f"hyb_cells_lt5_r{r}", d.pct_cells_lt5, p1(d.pct_cells_lt5),
                                            T / "F7_disclosure.csv", f"% of populated HYB cells < 5 people r={r}")
        rows.append(row)
    return pd.DataFrame(rows)


CAT_ORDER = ["match", "minor", "moderate", "major", "x-only", "y-only"]
CAT_NAMES = {"match": "Match (R < 0.05)", "minor": "Minor (0.05 ≤ R < 0.25)", "moderate": "Moderate (0.25 ≤ R < 0.50)",
             "major": "Major (R ≥ 0.50)"}
XY = {"PHH vs NAR": ("PHH", "NAR"), "HYB vs PHH": ("PHH", "HYB"), "HYB vs NAR": ("NAR", "HYB")}


def rel_long() -> pd.DataFrame:
    f = pd.read_csv(T / "F2_categories_relative.csv")
    cov = f[f.category.str.startswith("H5")]
    f = f[~f.category.str.startswith("H5")].copy()
    f["cat"] = [("x-only" if c.split("-")[0] == XY[p][0] else "y-only") if c.endswith("-only") else c
                for c, p in zip(f.category, f.pair)]
    for _, c in cov.iterrows():
        pv(f"rel_cov_cells_{c.pair.replace(' ', '')}_r{c.res}", int(c.n_cells), n0(c.n_cells),
           T / "F2_categories_relative.csv", f"cells with M >= 5, {c.pair}, r={c.res}")
        pv(f"rel_cov_pop_{c.pair.replace(' ', '')}_r{c.res}", c.pct_of_pop_M5, p2(c.pct_of_pop_M5),
           T / "F2_categories_relative.csv", f"share of M in cells with M >= 5, {c.pair}, r={c.res}")
    return f


def t3(f: pd.DataFrame, pair: str) -> pd.DataFrame:
    rows = []
    for c in CAT_ORDER:
        name = CAT_NAMES.get(c) or f"{XY[pair][0 if c == 'x-only' else 1]}-only"
        row = {"Category": name}
        for r in RS:
            v = f[(f.pair == pair) & (f.res == r) & (f.cat == c)]
            cells = v.pct_of_cells_M5.sum() if len(v) else 0.0
            pop = v.pct_of_pop_M5.sum() if len(v) else 0.0
            k = f"rel_{pair.replace(' ', '')}_{c}_r{r}"
            row[f"r={r} cells"] = pv(k + "_cells", cells, p1(cells), T / "F2_categories_relative.csv",
                                     f"{pair} {c}: % of cells (M>=5), r={r}")
            row[f"r={r} population"] = pv(k + "_pop", pop, p1(pop), T / "F2_categories_relative.csv",
                                          f"{pair} {c}: % of population M (M>=5), r={r}")
        rows.append(row)
    return pd.DataFrame(rows)


def t3_fixed() -> pd.DataFrame:
    f = pd.read_csv(T / "F2_categories_fixed.csv")
    f = f[f.pair == "PHH vs NAR"]
    order = ["major", "moderate", "minor", "match", "PHH-only", "NAR-only"]
    rows = []
    for c in order:
        row = {"Category": c}
        for r in RS:
            v = f[(f.res == r) & (f.agreement == c)].iloc[0]
            row[f"r={r} hexagons"] = pv(f"fixed_{c}_r{r}_cells", v.pct_of_hexes, p1(v.pct_of_hexes),
                                        T / "F2_categories_fixed.csv", f"fixed-threshold {c}: % of hexagons, r={r}")
            row[f"r={r} population"] = pv(f"fixed_{c}_r{r}_pop", v.pct_of_population, p1(v.pct_of_population),
                                          T / "F2_categories_fixed.csv", f"fixed-threshold {c}: % of population, r={r}")
        rows.append(row)
    return pd.DataFrame(rows)


def t4(db: pd.DataFrame) -> pd.DataFrame:
    P = db.POP.sum()
    pop = db[db.POP > 0]
    src = V2 / "db_table.parquet"
    rows = [("Populated Dissemination Blocks nationally", n0(len(pop)))]
    for s, lab in [("NAR", "Blocks allocated via NAR (τ = 50)"),
                   ("PHH", "Blocks allocated via PHH (zero or thin NAR coverage, τ = 50)")]:
        m = pop.s_final == s
        nb, pb, pp = int(m.sum()), 100 * m.mean(), 100 * pop.POP[m].sum() / P
        pv(f"tau50_{s.lower()}_dbs", nb, n0(nb), src, f"{s}-allocated blocks at tau=50")
        pv(f"tau50_{s.lower()}_pct_dbs", pb, p1(pb), src, f"{s}-allocated blocks, % of populated blocks")
        pv(f"tau50_{s.lower()}_pct_pop", pp, p2(pp), src, f"{s}-allocated blocks, % of population")
        rows.append((lab, f"{n0(nb)} ({p1(pb)} of blocks, {p1(pp)} of population)"))
    zc = pop.zero_cov
    thin = (pop.n > 0) & (pop.c > C.FINAL_TAU)
    pv("zero_cov_dbs", int(zc.sum()), n0(zc.sum()), src, "zero-coverage populated DBs (BU {1,2})")
    pv("zero_cov_pct_pop", 100 * pop.POP[zc].sum() / P, p2(100 * pop.POP[zc].sum() / P), src, "zero coverage % pop")
    pv("thin_tau50_dbs", int(thin.sum()), n0(thin.sum()), src, "thin-coverage DBs at tau=50")
    pv("thin_tau50_pct_pop", 100 * pop.POP[thin].sum() / P, p2(100 * pop.POP[thin].sum() / P), src,
       "thin-coverage DBs at tau=50, % pop")
    rows.append(("  of which zero coverage (n = 0)", f"{n0(zc.sum())} ({p2(100 * pop.POP[zc].sum() / P)} of population)"))
    rows.append(("  of which thin coverage (POP/n > 50)", f"{n0(thin.sum())} ({p2(100 * pop.POP[thin].sum() / P)} of population)"))
    for r in RS:
        s = summary(r)
        tot = pv(f"hyb_total_r{r}", s["total_hyb"], n0(s["total_hyb"]), V2 / f"res{r}" / "allocate_summary.json",
                 f"national HYB total r={r}")
        eps = pv(f"hyb_max_eps_r{r}", s["max_abs_eps_hyb"], f"{s['max_abs_eps_hyb']:.1e}",
                 V2 / f"res{r}" / "allocate_summary.json", f"max |eps(d)| HYB r={r}")
        rows.append((f"National population, hybrid layer, r = {r} (max DB error)", f"{tot} ({eps})"))
    rows.append(("National population, source DB totals", n0(P)))
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def t5() -> pd.DataFrame:
    sw = pd.read_csv(V2 / "tau_sweep.csv")
    tg = pd.read_csv(T / "tau_by_res.csv")
    rows = []
    for _, s in sw.iterrows():
        t = int(s.tau_people_per_point)
        row = {"τ": t,
               "Zero coverage, blocks (% pop)": f"{n0(s.n_zero_coverage_dbs)} ({p1(s.pct_pop_zero_coverage)})",
               "Additional thin coverage, blocks (% pop)": f"{n0(s.n_thin_coverage_dbs)} ({p1(s.pct_pop_thin_coverage)})",
               "Total PHH blocks": pv(f"sweep_tau{t}_phh_dbs", int(s.n_dbs_phh_total), n0(s.n_dbs_phh_total),
                                      V2 / "tau_sweep.csv", f"PHH blocks at tau={t}"),
               "Total PHH (% pop)": pv(f"sweep_tau{t}_phh_pct_pop", s.pct_pop_phh_total, p1(s.pct_pop_phh_total),
                                       V2 / "tau_sweep.csv", f"PHH % pop at tau={t}"),
               "Total NAR (% pop)": p1(s.pct_pop_nar_total)}
        pv(f"sweep_tau{t}_thin_dbs", int(s.n_thin_coverage_dbs), n0(s.n_thin_coverage_dbs), V2 / "tau_sweep.csv",
           f"thin-coverage blocks at tau={t}")
        for r in RS:
            g = tg[(tg.res == r) & (tg.tau == t)].iloc[0]
            row[f"D/P HYB vs NAR, r={r}"] = pv(f"tau{t}_dp_hyb_nar_r{r}", g.DP_hyb_vs_nar_pct, p2(g.DP_hyb_vs_nar_pct),
                                               T / "tau_by_res.csv", f"D/P HYB vs NAR at tau={t}, r={r}")
            pv(f"tau{t}_dp_hyb_phh_r{r}", g.DP_hyb_vs_phh_pct, p2(g.DP_hyb_vs_phh_pct), T / "tau_by_res.csv",
               f"D/P HYB vs PHH at tau={t}, r={r}")
        rows.append(row)
    return pd.DataFrame(rows)


def t_ablation() -> pd.DataFrame:
    a = pd.read_csv(T / "ablation_res8.csv")
    cell = "882b9bc711fffff"
    rows = []
    for _, x in a.iterrows():
        k = f"abl_{x.tag}"
        src = T / "ablation_res8.csv"
        rows.append({
            "Run": x.run,
            "NAR locations used": pv(k + "_nar_used", int(x.nar_locations_used), n0(x.nar_locations_used), src, f"{x.run}: NAR locations used"),
            "Zero-coverage DBs": pv(k + "_zero_cov", int(x.zero_coverage_dbs), n0(x.zero_coverage_dbs), src, f"{x.run}: zero-coverage DBs"),
            "PHH share of population, τ = 50": pv(k + "_phh_pct_pop", x.phh_source_pct_pop_tau50, p2(x.phh_source_pct_pop_tau50), src, f"{x.run}: PHH % pop at tau=50"),
            "D/P PHH vs NAR": pv(k + "_dp_phh_nar", x.DP_phh_vs_nar_pct, p2(x.DP_phh_vs_nar_pct), src, f"{x.run}: D/P PHH vs NAR r=8"),
            "D/P HYB vs PHH": pv(k + "_dp_hyb_phh", x.DP_hyb_vs_phh_pct, p2(x.DP_hyb_vs_phh_pct), src, f"{x.run}: D/P HYB vs PHH r=8"),
            "D/P HYB vs NAR": pv(k + "_dp_hyb_nar", x.DP_hyb_vs_nar_pct, p2(x.DP_hyb_vs_nar_pct), src, f"{x.run}: D/P HYB vs NAR r=8"),
            f"{cell} PHH / NAR / HYB": pv(k + "_toronto", (x[f"{cell}_phh"], x[f"{cell}_nar"], x[f"{cell}_hyb"]),
                                          f"{x[f'{cell}_phh']:,.1f} / {x[f'{cell}_nar']:,.1f} / {x[f'{cell}_hyb']:,.1f}",
                                          src, f"{x.run}: Toronto cell values"),
        })
    return pd.DataFrame(rows)


def t_multires() -> tuple[pd.DataFrame, pd.DataFrame]:
    f1 = pd.read_csv(T / "F1_core_metrics.csv")
    f3 = pd.read_csv(T / "F3_forced.csv").set_index("res")
    f7 = pd.read_csv(T / "F7_disclosure.csv")
    f4 = pd.read_csv(T / "F4_decomposition.csv").set_index("pair")
    rows = []

    def add(section, metric, key, vals, fmt, src, desc):
        row = {"Section": section, "Metric": metric}
        for r, v in zip(RS, vals):
            row[f"r = {r}"] = pv(f"{key}_r{r}", v, fmt(v), src, f"{desc}, r={r}")
        rows.append(row)

    for pair in PAIRS:
        g = f1[(f1.tag == "v2") & (f1.pair == pair)].set_index("res").reindex(RS)
        k = pair.replace(" ", "").replace("vs", "_")
        s = T / "F1_core_metrics.csv"
        add(pair, "Populated cells, union", f"{k}_n_union", g.n_union, n0, s, f"{pair} union cells")
        add(pair, "Populated cells, both", f"{k}_n_both", g.n_both, n0, s, f"{pair} cells populated in both")
        add(pair, "Displaced population D", f"{k}_D", g.D, n0, s, f"{pair} D")
        add(pair, "D/P", f"{k}_DP", 100 * g.D_over_P, p2, s, f"{pair} D/P %")
        add(pair, "Pearson r", f"{k}_pearson", g.pearson_r, lambda v: f"{v:.5f}", s, f"{pair} Pearson r")
        add(pair, "Pearson r (log1p)", f"{k}_pearson_log1p", g.pearson_r_log1p, lambda v: f"{v:.4f}", s, f"{pair} r log1p")
        add(pair, "Spearman ρ", f"{k}_spearman", g.spearman_rho, lambda v: f"{v:.4f}", s, f"{pair} Spearman")
        add(pair, "Bland–Altman 95% limits (±)", f"{k}_loa", g.ba_loa_upper, lambda v: f"±{v:,.1f}", s, f"{pair} LoA")
        add(pair, "MARD, cells with M ≥ 5", f"{k}_mard5", g.mard_min5, lambda v: f"{v:.3f}", s, f"{pair} MARD M>=5")
        if pair == "PHH vs NAR":
            s3 = T / "F3_forced.csv"
            add(pair, "Populated DBs in forced agreement", "forced_pct_dbs", f3.pct_dbs_forced.reindex(RS), p1, s3,
                "% populated DBs forced")
            add(pair, "Population in forced-agreement DBs", "forced_pct_pop", f3.pct_pop_forced.reindex(RS), p1, s3,
                "% population in forced DBs")
            add(pair, "D / population of non-forced DBs", "dp_nonforced", f3.D_over_pop_non_forced_pct.reindex(RS),
                p2, s3, "D over non-forced population %")
    s7 = T / "F7_disclosure.csv"
    for lay in ["PHH", "NAR", "HYB"]:
        g = f7[f7.layer == lay].set_index("res").reindex(RS)
        add(f"Disclosure, {lay}", "Populated cells < 5 people", f"{lay.lower()}_pct_cells_lt5", g.pct_cells_lt5, p1, s7,
            f"{lay} % cells < 5")
        add(f"Disclosure, {lay}", "Population in cells < 5", f"{lay.lower()}_pct_pop_lt5", g.pct_pop_in_cells_lt5, p2,
            s7, f"{lay} % pop in cells < 5")
        add(f"Disclosure, {lay}", "Populated cells < 10 people", f"{lay.lower()}_pct_cells_lt10", g.pct_cells_lt10, p1,
            s7, f"{lay} % cells < 10")
    s4 = T / "F4_decomposition.csv"
    dec = []
    for pair in PAIRS:
        x = f4.loc[pair]
        k = pair.replace(" ", "").replace("vs", "_")
        dec.append({"Pair": pair,
                    "D8": pv(f"{k}_F4_D8", x.D8, n0(x.D8), s4, f"{pair} D8"),
                    "Offsets within the r = 7 parent": pv(f"{k}_F4_local", x.pct_local_resolves_within_res7_parent,
                                                         p1(x.pct_local_resolves_within_res7_parent), s4, f"{pair} % local"),
                    "Persists to r = 7, offsets within the r = 6 parent": pv(
                        f"{k}_F4_r7", x.pct_persists_to_res7_resolves_within_res6,
                        p1(x.pct_persists_to_res7_resolves_within_res6), s4, f"{pair} % resolved within r6"),
                    "Persists at r = 6": pv(f"{k}_F4_r6", x.pct_persists_to_res6, p1(x.pct_persists_to_res6), s4,
                                            f"{pair} % persists to r6"),
                    "Identity residual": f"{x.identity_residual:.1e}"})
    return pd.DataFrame(rows), pd.DataFrame(dec)


def ts_province() -> pd.DataFrame:
    f = pd.read_csv(T / "F6_by_province.csv", dtype={"stratum": str})
    rows = []
    for pr, name in PR_NAMES.items():
        row = {"Province or territory": name}
        for pair in PAIRS:
            for r in RS:
                v = f[(f.stratum == pr) & (f.res == r) & (f.pair == pair)].iloc[0]
                row[f"{pair}, r={r}"] = pv(f"pr{pr}_{pair.replace(' ', '')}_r{r}", v.D_over_P_pct, p2(v.D_over_P_pct),
                                           T / "F6_by_province.csv", f"D/P {pair}, {name}, r={r}")
        rows.append(row)
    return pd.DataFrame(rows)


def extra_values() -> None:
    """Values cited in the text that are not in a manuscript table."""
    # urban-rural strata (F6)
    f = pd.read_csv(T / "F6_by_popctr.csv")
    for _, x in f.iterrows():
        pv(f"popctr{x.stratum.split()[0]}_{x.pair.replace(' ', '')}_r{x.res}", x.D_over_P_pct, p2(x.D_over_P_pct),
           T / "F6_by_popctr.csv", f"D/P {x.pair}, {x.stratum}, r={x.res}")
    # Toronto (F5)
    s = pd.read_csv(T / "F5_toronto_summary.csv")
    for _, x in s.iterrows():
        k = f"toronto_{x.tag}_r{x.res}"
        for c in ["PHH", "NAR", "HYB", "delta", "G"]:
            pv(f"{k}_{c}", x[c], f"{x[c]:,.1f}", T / "F5_toronto_summary.csv", f"Toronto {x.h3} {c} ({x.tag})")
        pv(f"{k}_n_dbs", int(x.n_dbs), n0(x.n_dbs), T / "F5_toronto_summary.csv", f"Toronto {x.h3} contributing DBs")
        pv(f"{k}_top3", x.top3_share_of_G_pct, p1(x.top3_share_of_G_pct), T / "F5_toronto_summary.csv",
           f"Toronto {x.h3} top-3 DB share of G")
    tr = pd.read_csv(T / "F5_tracked_dbs.csv", dtype={"DBUID": str})
    for _, x in tr[tr.tag == "v2"].iterrows():
        pv(f"tracked_{x.DBUID}_r{x.res}_delta", x.delta_in_toronto_cell, f"{x.delta_in_toronto_cell:,.1f}",
           T / "F5_tracked_dbs.csv", f"DB {x.DBUID} ({x.role}) delta in Toronto cell, r={x.res}")
        pv(f"tracked_{x.DBUID}_r{x.res}_Dd", x.D_d_all_cells, f"{x.D_d_all_cells:,.1f}", T / "F5_tracked_dbs.csv",
           f"DB {x.DBUID} ({x.role}) own displacement D_d, r={x.res}")
    # vintage (M3)
    v = pd.read_csv(T / "vintage_flag_summary.csv")
    for _, x in v.iterrows():
        g = f"{x.gamma:g}"
        pv(f"vint_g{g}_dbs", int(x.n_flagged), n0(x.n_flagged), T / "vintage_flag_summary.csv", f"flagged DBs, gamma={g}")
        pv(f"vint_g{g}_pct_pop", x.pct_pop_flagged, p2(x.pct_pop_flagged), T / "vintage_flag_summary.csv",
           f"flagged % pop, gamma={g}")
        pv(f"vint_g{g}_already_phh", int(x.flagged_already_phh_tau50_base), n0(x.flagged_already_phh_tau50_base),
           T / "vintage_flag_summary.csv", f"flagged DBs already PHH-sourced at tau=50, gamma={g}")
    # HYB-V
    f1 = pd.read_csv(T / "F1_core_metrics.csv")
    for _, x in f1[f1.tag == "v2_hybv"].iterrows():
        pv(f"hybv_{x.pair.replace(' ', '')}_DP_r{x.res}", 100 * x.D_over_P, p2(100 * x.D_over_P),
           T / "F1_core_metrics.csv", f"D/P {x.pair} (HYB-V), r={x.res}")
    # validation
    v4 = pd.read_csv(T / "validation_V4_nesting.csv")
    for _, x in v4[v4.tag == "v2"].iterrows():
        k = f"V4_{x.method}_{x.from_res}to{x.to_res}"
        pv(k + "_DP", x.D_over_P_pct, p2(x.D_over_P_pct), T / "validation_V4_nesting.csv",
           f"V4 parent aggregation vs direct, {x.method} {x.from_res}->{x.to_res}, D/P")
        pv(k + "_gt1", int(x.n_cells_diff_gt1), n0(x.n_cells_diff_gt1), T / "validation_V4_nesting.csv",
           f"V4 cells differing by > 1 person, {x.method} {x.from_res}->{x.to_res}")
        pv(k + "_max", x.max_abs_diff, f"{x.max_abs_diff:,.1f}", T / "validation_V4_nesting.csv",
           f"V4 max abs difference, {x.method} {x.from_res}->{x.to_res}")
    v6 = pd.read_csv(T / "validation_V6_hierarchical.csv")
    for _, x in v6.iterrows():
        e = "nar" if "NAR" in x.estimator else "areal"
        for c, f_ in [("MAE", lambda z: f"{z:.2f}"), ("RMSE", lambda z: f"{z:.1f}"),
                      ("median_APE_M5", lambda z: f"{z:.3f}"), ("D_over_P_pct", p2)]:
            pv(f"V6_{e}_r{x.res}_{c}", x[c], f_(x[c]), T / "validation_V6_hierarchical.csv",
               f"V6 {x.estimator} {c}, r={x.res}")
    # fallback tiers and layer totals
    for r in RS:
        s = summary(r)
        src = V2 / f"res{r}" / "allocate_summary.json"
        for t in ("1", "2", "3"):
            pv(f"fallback_tier{t}_r{r}_dbs", s["fallback"][t]["n_dbs"], n0(s["fallback"][t]["n_dbs"]), src,
               f"NAR areal fallback tier {t} DBs, r={r}")
            pv(f"fallback_tier{t}_r{r}_pop", s["fallback"][t]["pop"], n0(s["fallback"][t]["pop"]), src,
               f"NAR areal fallback tier {t} population, r={r}")
    # forced-agreement and rural strata by number of DBs per cell are in F3_by_n_dbs.csv (supplement only)
    extra_values_h()


def extra_values_h() -> None:
    """Further values cited in the Phase H manuscript text."""
    # Toronto r = 8 decomposition (v2): leading contributors and the three DBs tracked from the preprint
    d = pd.read_csv(T / "F5_toronto_decomposition.csv", dtype={"DBUID": str})
    src = T / "F5_toronto_decomposition.csv"
    for tag in ("v2", "v1"):
        x = d[(d.tag == tag) & (d.res == 8)].sort_values("share_of_G_pct", ascending=False)
        keep = list(x.DBUID[:4]) + [k for k in ("35204565001", "35204004008", "35204004007") if k not in list(x.DBUID[:4])]
        for _, y in x[x.DBUID.isin(keep)].iterrows():
            k = f"tor_{tag}_{y.DBUID}"
            pv(k + "_POP", y.POP, n0(y.POP), src, f"DB {y.DBUID} population ({tag})")
            pv(k + "_n", int(y.n), n0(y.n), src, f"DB {y.DBUID} NAR locations ({tag})")
            pv(k + "_c", y.c, f"{y.c:.1f}", src, f"DB {y.DBUID} people per NAR location ({tag})")
            pv(k + "_phh", y.pop_phh, f"{y.pop_phh:,.1f}", src, f"DB {y.DBUID} PHH contribution to 882b9bc711fffff ({tag})")
            pv(k + "_nar", y.pop_nar, f"{y.pop_nar:,.1f}", src, f"DB {y.DBUID} NAR contribution to 882b9bc711fffff ({tag})")
            pv(k + "_share", y.share_of_G_pct, p1(y.share_of_G_pct), src, f"DB {y.DBUID} share of G ({tag})")
            pv(k + "_s", y.s_final, str(y.s_final), src, f"DB {y.DBUID} hybrid source ({tag})")
    # F4 by DB class (PHH vs NAR)
    f = pd.read_csv(T / "F4_by_db_class.csv")
    for _, x in f[f.pair == "PHH vs NAR"].iterrows():
        c = x.db_class.split()[0]
        for col in ("pct_local_8to7", "pct_7to6", "pct_persists_to_6", "share_of_pair_DB_displacement_res8_pct"):
            pv(f"F4class_{c}_{col}", x[col], p1(x[col]), T / "F4_by_db_class.csv", f"F4 PHH vs NAR, {x.db_class}, {col}")
    # validation V1, V3, V5
    v1 = pd.read_csv(T / "validation_V1_db_conservation.csv")
    pv("V1_max_eps", v1.max_abs_eps.max(), f"{v1.max_abs_eps.max():.1e}", T / "validation_V1_db_conservation.csv",
       "V1 max |eps(d)| over all layers and r")
    pv("V1_n_layers", len(v1), str(len(v1)), T / "validation_V1_db_conservation.csv", "V1 number of method x r layers")
    v3 = pd.read_csv(T / "validation_V3_invariance.csv")
    m3 = v3[v3.check.str.startswith("DB total")].max_abs_diff_across_r.max()
    pv("V3_max_diff", m3, f"{m3:.1e}", T / "validation_V3_invariance.csv", "V3 max DB-total difference across r")
    v5 = pd.read_csv(T / "validation_V5_fallback.csv")
    for _, x in v5.iterrows():
        for lay in ("nar", "hyb", "phh"):
            pv(f"V5_{lay}_pct_cells_lt1_r{x.res}", x[f"{lay}_pct_cells_lt1"], p1(x[f"{lay}_pct_cells_lt1"]),
               T / "validation_V5_fallback.csv", f"% of {lay.upper()} cells with population < 1, r={x.res}")
        pv(f"V5_nar_only_cells_r{x.res}", int(x.nar_only_cells), n0(x.nar_only_cells), T / "validation_V5_fallback.csv",
           f"NAR-only cells, r={x.res}")
    # vintage distribution
    vp = pd.read_csv(T / "vintage_by_popctr.csv", index_col=[0, 1])
    pv("vint_share_cma", vp.loc[("cma_type", "B CMA"), "share_of_all_flagged_pop"],
       p1(vp.loc[("cma_type", "B CMA"), "share_of_all_flagged_pop"]), T / "vintage_by_popctr.csv", "share of flagged pop in CMAs")
    pv("vint_share_large_urban", vp.loc[("popctr_class", "4 large urban population centre"), "share_of_all_flagged_pop"],
       p1(vp.loc[("popctr_class", "4 large urban population centre"), "share_of_all_flagged_pop"]), T / "vintage_by_popctr.csv",
       "share of flagged pop in large urban population centres")
    vr = pd.read_csv(T / "vintage_by_pr.csv", dtype={"PR": str}).set_index("PR")
    for pr in ("24", "35", "48", "59"):
        pv(f"vint_share_pr{pr}", vr.loc[pr, "share_of_all_flagged_pop"], p1(vr.loc[pr, "share_of_all_flagged_pop"]),
           T / "vintage_by_pr.csv", f"share of flagged pop in {PR_NAMES[pr]}")
    vc = pd.read_csv(T / "vintage_by_cma.csv").iloc[0]
    pv("vint_top_cma_pop", vc.pop_flagged, n0(vc.pop_flagged), T / "vintage_by_cma.csv", f"flagged pop in {vc.iloc[0]}")
    # national re-ranking (F5)
    b = pd.read_csv(T / "F5_rerank_by_cma.csv")
    for r in RS:
        for rb, place in (("abs_delta", "Toronto"), ("R_M5", "Outside CMAs and CAs"), ("abs_delta", "Outside CMAs and CAs")):
            x = b[(b.res == r) & (b.ranked_by == rb) & (b.place == place)]
            v = x.share_top_cells_pct.iloc[0] if len(x) else 0.0
            pv(f"rerank_{rb}_{place.split()[0]}_r{r}", v, p1(v), T / "F5_rerank_by_cma.csv",
               f"share of top-500 cells by {rb} in {place}, r={r}")
    for place in ("Toronto", "Outside CMAs and CAs"):
        v = b[b.place == place].share_pop_pct.iloc[0]
        pv(f"rerank_pop_{place.split()[0]}", v, p1(v), T / "F5_rerank_by_cma.csv", f"share of national population in {place}")
    # MARD over the full union
    f1 = pd.read_csv(T / "F1_core_metrics.csv")
    for _, x in f1[f1.tag == "v2"].iterrows():
        pv(f"{x.pair.replace(' ', '').replace('vs', '_')}_mard0_r{x.res}", x.mard_min0, f"{x.mard_min0:.3f}",
           T / "F1_core_metrics.csv", f"{x.pair} MARD over all union cells, r={x.res}")
    # ablation details
    a = pd.read_csv(T / "ablation_res8.csv").set_index("tag")
    for tag in a.index:
        pv(f"abl_{tag}_unassigned_pip", int(a.loc[tag, "nar_unassigned_pip"]), n0(a.loc[tag, "nar_unassigned_pip"]),
           T / "ablation_res8.csv", f"{tag}: NAR locations outside every DB")
        pv(f"abl_{tag}_phh_dbs", int(a.loc[tag, "phh_source_dbs_tau50"]), n0(a.loc[tag, "phh_source_dbs_tau50"]),
           T / "ablation_res8.csv", f"{tag}: PHH-sourced DBs at tau=50")
    drop = int(a.loc["v1", "nar_locations_used"] - a.loc["v1_M1", "nar_locations_used"])
    pv("M1_dropped", drop, n0(drop), T / "ablation_res8.csv", "NAR locations removed by the BU {1,2} filter (v1 vs v1+M1)")
    # forced-agreement counts
    f3 = pd.read_csv(T / "F3_forced.csv").set_index("res")
    for r in RS:
        pv(f"forced_dbs_r{r}", int(f3.loc[r, "forced_dbs"]), n0(f3.loc[r, "forced_dbs"]), T / "F3_forced.csv", f"forced DBs, r={r}")
        pv(f"forced_contrib_pct_pop_r{r}", f3.loc[r, "pct_pop_forced_contrib_def"], p1(f3.loc[r, "pct_pop_forced_contrib_def"]),
           T / "F3_forced.csv", f"population in forced DBs, contribution-based definition, r={r}")
    # GAF total and the excluded water DBs
    g = pd.read_csv(C.GAF_CSV, usecols=[C.GAF_DBUID_COL, C.GAF_POP_COL], dtype={C.GAF_DBUID_COL: str}, encoding="latin1")
    ex = g[g[C.GAF_DBUID_COL].isin(C.EXCLUDED_DBUIDS)][C.GAF_POP_COL].sum()
    pv("gaf_total_pop", g[C.GAF_POP_COL].sum(), n0(g[C.GAF_POP_COL].sum()), C.GAF_CSV, "GAF national total")
    pv("excluded_pop", ex, n0(ex), C.GAF_CSV, "population in the two populated DBs without a cartographic polygon")
    pv("edge_r8_m", edge(8) * 1000, n0(edge(8) * 1000), H3_SRC, "mean edge length at r=8 (m)")


def to_md(title: str, df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = [f"### {title}", "", "| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    log = Log(T / "phaseG_tables_log.txt")
    db = pd.read_parquet(V2 / "db_table.parquet")
    f = rel_long()
    multires, dec = t_multires()
    tables = [
        ("T1_study_area", "Table 1. Study area and processed data volumes (v2)", t1(db)),
        ("T2_data_sources", "Table 2. Data sources", t2()),
        ("T_resolution_spec", "Table R. H3 resolutions used (h3 v4 means) and layer properties", t_res()),
        ("T3_relative_by_res", "Table 3. Relative agreement categories, PHH vs NAR, cells with M ≥ 5", t3(f, "PHH vs NAR")),
        ("T3_relative_all_pairs", "Table S. Relative agreement categories, all pairs",
         pd.concat([t3(f, p).assign(Pair=p) for p in PAIRS])),
        ("T3_fixed_by_res", "Table S. Preprint fixed-threshold categories, PHH vs NAR, by r", t3_fixed()),
        ("T4_hybrid_summary", "Table 4. Hybrid allocation summary, v2, τ = 50", t4(db)),
        ("T5_tau_sensitivity", "Table 5. Sensitivity to τ, v2", t5()),
        ("T_ablation", "Table A. Ablation at r = 8", t_ablation()),
        ("T_multires_summary", "Table M. Multi-resolution comparison summary", multires),
        ("T_decomposition", "Table D. Decomposition of D at r = 8 (F4)", dec),
        ("TS_province_by_res", "Table S. D/P (%) by province or territory and resolution", ts_province()),
    ]
    extra_values()
    md = ["# Phase G manuscript tables (v2)", "",
          "Written by `05_pipeline_v2/08_tables.py`. Every value is read from the Phase C to F outputs; "
          "sources are listed in `paper_values_v2.md`.", ""]
    for name, title, df in tables:
        df.to_csv(OUT / f"{name}.csv", index=False)
        md.append(to_md(f"{title} (`{name}.csv`)", df))
        log(f"wrote {name}.csv ({len(df)} rows)")
    (OUT / "tables_v2.md").write_text("\n".join(md))

    pvd = pd.DataFrame(PV).drop_duplicates(["key", "value", "source"])   # a table built twice reports a value twice
    dup = pvd.key[pvd.key.duplicated()]
    if len(dup):
        raise RuntimeError(f"duplicate paper_values keys: {sorted(set(dup))[:10]}")
    pvd.drop(columns="raw").to_csv(OUT / "paper_values_v2.csv", index=False)
    lines = ["# paper_values_v2", "",
             "Every number used in the revised manuscript, with the file it comes from. Written by "
             "`05_pipeline_v2/08_tables.py`; do not edit by hand. Paths are relative to `Analysis/hexagonPops/`. "
             "Method version v2 (BU {1, 2} filter, digital DB boundary), τ = 50, base hybrid unless stated.", "",
             f"{len(pvd)} values.", "", "| Key | Value | Description | Source |", "|---|---|---|---|"]
    for _, x in pvd.iterrows():
        lines.append(f"| `{x.key}` | {x.value} | {x.description} | `{x.source}` |")
    (C.TABLES / "paper_values_v2.md").write_text("\n".join(lines) + "\n")
    log(f"wrote paper_values_v2.md ({len(pvd)} values)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
