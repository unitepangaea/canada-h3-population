"""Core allocation logic, ported from 01_final_pipeline/ without changing the algorithms.

Sources:
  phh_h3_population_canada.py / rebuild_comparison_python.py  -> phh_contrib (Eq. 2)
  rebuild_nar_layer_python.py                                  -> nar_point_contrib (Eq. 4),
                                                                  areal_fallback (Eq. 5, two tiers)
  hybrid_threshold_sweep.py                                    -> source_assignment, tau_sweep (Eqs. 9-11)

H3 cells are held as int64 internally (h3.api.basic_int) and converted to strings on output.
All functions are pure (no file IO) so they can be unit-tested on synthetic data.
"""
from __future__ import annotations

import h3
import h3.api.basic_int as h3i
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Polygon

# ----------------------------------------------------------------------------
# Cells
# ----------------------------------------------------------------------------

def tag_cells(lat, lon, res: int) -> np.ndarray:
    """latlng_to_cell for every point; returns int64 H3 indices (design rule 1: bin directly at r)."""
    lat = np.asarray(lat, dtype="float64")
    lon = np.asarray(lon, dtype="float64")
    f = h3i.latlng_to_cell
    return np.fromiter((f(a, b, res) for a, b in zip(lat.tolist(), lon.tolist())),
                       dtype=np.int64, count=len(lat))


def cells_to_str(cells) -> list[str]:
    return [h3.int_to_str(int(c)) for c in cells]


def cell_polygons(cells) -> list[Polygon]:
    out = []
    for c in cells:
        b = h3i.cell_to_boundary(int(c))
        out.append(Polygon([(lng, lat) for lat, lng in b]))
    return out


# ----------------------------------------------------------------------------
# Point-in-polygon (DB assignment for NAR locations)
# ----------------------------------------------------------------------------

def points_in_polygons(lon, lat, polygons, chunk: int = 1_000_000):
    """Index of the polygon containing each point (predicate 'within'), or -1.

    Equivalent to gpd.sjoin(points, polys, predicate="within", how="inner") in the preprint
    code. A point inside more than one polygon keeps the first match; the number of such
    points is returned so the caller can log it (sjoin would have duplicated them).
    """
    polygons = np.asarray(polygons)
    tree = shapely.STRtree(polygons)
    lon = np.asarray(lon, dtype="float64")
    lat = np.asarray(lat, dtype="float64")
    out = np.full(len(lon), -1, dtype=np.int64)
    n_multi = 0
    for s in range(0, len(lon), chunk):
        pts = shapely.points(lon[s:s + chunk], lat[s:s + chunk])
        ip, ig = tree.query(pts, predicate="within")
        if len(ip):
            first = np.r_[True, ip[1:] != ip[:-1]]
            n_multi += int((~first).sum())
            out[s + ip[first]] = ig[first]
    return out, n_multi


# ----------------------------------------------------------------------------
# Hybrid source assignment (Eqs. 9-11)
# ----------------------------------------------------------------------------

def source_assignment(pop: pd.Series, n: pd.Series, tau: float | None) -> pd.Series:
    """'PHH', 'NAR' or 'n/a' per DB. Depends only on POP(d) and n(d), so it is the same at every r.

    Zero coverage: POP > 0 and n = 0. Thin coverage: POP > 0 and POP / n > tau (strict).
    Zero-population DBs are 'n/a' (fix for review item 3.2f in hybrid_threshold_sweep.py).
    """
    pop = pop.astype("float64")
    n = n.astype("float64")
    populated = pop > 0
    zero = populated & (n == 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ppp = np.where(n > 0, pop / n.where(n > 0, 1.0), np.nan)
    thin = populated & (n > 0) & (ppp > tau) if tau is not None else pd.Series(False, index=pop.index)
    s = pd.Series(np.where(populated, "NAR", "n/a"), index=pop.index, dtype=object)
    s[zero | thin] = "PHH"
    return s


def tau_sweep(pop: pd.Series, n: pd.Series, taus) -> pd.DataFrame:
    """Same columns as output/threshold_sweep_results.csv (hybrid_threshold_sweep.run_threshold_sweep)."""
    populated = pop > 0
    p = pop[populated].astype("float64")
    nn = n[populated].astype("float64")
    total = p.sum()
    zero = nn == 0
    n_zero, pop_zero = int(zero.sum()), p[zero].sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        ppp = pd.Series(np.where(nn > 0, p / nn.where(nn > 0, 1.0), np.nan), index=p.index)
    rows = []
    for tau in taus:
        thin = (ppp > tau) & ~zero
        n_thin, pop_thin = int(thin.sum()), p[thin].sum()
        rows.append({
            "tau_people_per_point": tau,
            "n_zero_coverage_dbs": n_zero,
            "pct_pop_zero_coverage": round(100 * pop_zero / total, 3),
            "n_thin_coverage_dbs": n_thin,
            "pct_pop_thin_coverage": round(100 * pop_thin / total, 3),
            "n_dbs_phh_total": n_zero + n_thin,
            "pct_pop_phh_total": round(100 * (pop_zero + pop_thin) / total, 3),
            "n_dbs_nar_total": int(len(p) - n_zero - n_thin),
            "pct_pop_nar_total": round(100 * (1 - (pop_zero + pop_thin) / total), 3),
            "pop_phh_total": pop_zero + pop_thin,
            "pop_total": total,
        })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Contributions (DBUID, h3) -> population
# ----------------------------------------------------------------------------

def phh_contrib(dbuid, pop, cells) -> pd.DataFrame:
    """Eq. 2: sum PHH point population by (DB, cell)."""
    df = pd.DataFrame({"DBUID": dbuid, "h3": cells, "pop_phh": np.asarray(pop, dtype="float64")})
    return df.groupby(["DBUID", "h3"], as_index=False, sort=False)["pop_phh"].sum()


def nar_point_contrib(dbuid, cells, db_pop: pd.Series) -> pd.DataFrame:
    """Eq. 4: each location in DB d receives POP(d) / n(d); summed by (DB, cell).

    Only DBs with POP > 0 contribute. n(d) is the number of locations passed in for d,
    so the caller applies the BU filter and DB universe before calling.
    """
    df = pd.DataFrame({"DBUID": dbuid, "h3": cells})
    n = df.groupby("DBUID").size()
    pop = db_pop.reindex(n.index).fillna(0.0)
    share = (pop / n)
    df["pop_nar"] = df["DBUID"].map(share).astype("float64")
    df = df[df["pop_nar"] > 0]
    out = df.groupby(["DBUID", "h3"], as_index=False, sort=False)["pop_nar"].sum()
    out["nar_tier"] = np.int8(0)
    return out


def _polygon_parts(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type in ("MultiPolygon", "GeometryCollection"):
        return [g for g in geom.geoms if g.geom_type == "Polygon"]
    return []


def areal_fallback(geoms: pd.Series, db_pop: pd.Series, res: int):
    """Eq. 5 for DBs with zero NAR coverage (NAR-only layer; the hybrid never uses it).

    Tier 1: every cell at resolution res whose centre lies in the DB polygon (geo_to_cells, per
            polygon part), equal shares.
    Tier 2: the cell containing the polygon's representative_point (always on the polygon).
    Tier 3: could not allocate; returned for logging, never pooled silently.

    geoms: shapely geometries in EPSG:4326 indexed by DBUID. Returns (contrib, unallocated).
    """
    recs_db, recs_h3, recs_pop, recs_tier = [], [], [], []
    unallocated = []
    for dbuid, geom in geoms.items():
        pop = float(db_pop.get(dbuid, 0.0))
        if pop <= 0:
            continue
        cells = []
        for g in _polygon_parts(geom):
            try:
                cells.extend(c for c in h3i.geo_to_cells(g, res) if c)
            except Exception as e:  # noqa: BLE001 - logged, tier 2 follows
                print(f"    geo_to_cells failed for DBUID {dbuid}: {e}")
        if cells:
            share = pop / len(cells)
            recs_db += [dbuid] * len(cells)
            recs_h3 += cells
            recs_pop += [share] * len(cells)
            recs_tier += [1] * len(cells)
            continue
        try:
            p = geom.representative_point()
            c = h3i.latlng_to_cell(p.y, p.x, res)
            if c:
                recs_db.append(dbuid)
                recs_h3.append(c)
                recs_pop.append(pop)
                recs_tier.append(2)
                continue
        except Exception as e:  # noqa: BLE001
            print(f"    representative_point failed for DBUID {dbuid}: {e}")
        unallocated.append({"DBUID": dbuid, "POP": pop,
                            "geom_type": None if geom is None else geom.geom_type})
    contrib = pd.DataFrame({"DBUID": recs_db, "h3": np.asarray(recs_h3, dtype=np.int64),
                            "pop_nar": np.asarray(recs_pop, dtype="float64"),
                            "nar_tier": np.asarray(recs_tier, dtype=np.int8)})
    contrib = contrib.groupby(["DBUID", "h3"], as_index=False, sort=False).agg(
        pop_nar=("pop_nar", "sum"), nar_tier=("nar_tier", "max"))
    return contrib, pd.DataFrame(unallocated, columns=["DBUID", "POP", "geom_type"])


def long_table(phh_c: pd.DataFrame, nar_c: pd.DataFrame, source: pd.Series) -> pd.DataFrame:
    """Long contribution table (DBUID, h3, pop_phh, pop_nar, pop_hyb, nar_tier, src_hyb).

    pop_hyb takes the PHH contribution for DBs with s(d) = PHH and the NAR contribution
    otherwise. NAR-source DBs always have n(d) > 0, so pop_hyb never uses the areal fallback.
    DBs without a source (outside the universe, or POP = 0) get pop_hyb = 0.
    """
    lt = phh_c.merge(nar_c, on=["DBUID", "h3"], how="outer")
    lt["pop_phh"] = lt["pop_phh"].fillna(0.0)
    lt["pop_nar"] = lt["pop_nar"].fillna(0.0)
    lt["nar_tier"] = lt["nar_tier"].fillna(-1).astype("int8")   # -1 = no NAR contribution
    src = lt["DBUID"].map(source).fillna("n/a")
    lt["src_hyb"] = src.astype("category")
    lt["pop_hyb"] = np.where(src == "PHH", lt["pop_phh"],
                             np.where(src == "NAR", lt["pop_nar"], 0.0))
    return lt


def build_contributions(pop: pd.Series, source: pd.Series, fallback_geoms: pd.Series,
                        phh_dbuid, phh_pop, phh_cells, nar_dbuid, nar_cells, res: int):
    """Assemble the long table for one resolution (used by 03_allocate.py and the tests).

    pop, source: indexed by DBUID (the DB universe). fallback_geoms: EPSG:4326 polygons of the
    zero-coverage DBs, indexed by DBUID. nar_* are the active locations (filter already applied).
    Returns (long_table, fallback_contrib, unallocated).
    """
    phh_c = phh_contrib(phh_dbuid, phh_pop, phh_cells)
    nar_c = nar_point_contrib(nar_dbuid, nar_cells, pop)
    fb_c, unalloc = areal_fallback(fallback_geoms, pop, res)
    lt = long_table(phh_c, pd.concat([nar_c, fb_c], ignore_index=True), source)
    return lt, fb_c, unalloc


def hex_table(lt: pd.DataFrame, method: str, res: int, low_count: float) -> pd.DataFrame:
    """Hexagon layer attributes (without geometry) for method in {'phh', 'nar', 'hyb'}."""
    col = f"pop_{method}"
    sub = lt.loc[lt[col] > 0, ["DBUID", "h3", col] + (["nar_tier"] if method == "nar" else [])
                 + (["src_hyb"] if method == "hyb" else [])]
    g = sub.groupby("h3", sort=True)
    out = pd.DataFrame({"population": g[col].sum(), "n_dbs_contributing": g["DBUID"].nunique()})
    if method == "hyb":
        phh_part = sub.loc[sub["src_hyb"] == "PHH"].groupby("h3")[col].sum()
        out["share_pop_from_phh_source"] = (phh_part.reindex(out.index).fillna(0.0) / out["population"])
    if method == "nar":
        out["fallback_tier"] = g["nar_tier"].max().astype("int8")   # 0 points only; 1 or 2 highest tier
    out = out[out["population"] > 0].reset_index()
    out.insert(1, "res", np.int8(res))
    out["low_count_flag"] = out["population"] < low_count
    return out


def db_totals(lt: pd.DataFrame) -> pd.DataFrame:
    """Per-DB sums of each method's contributions, for the conservation check (V1)."""
    return lt.groupby("DBUID")[["pop_phh", "pop_nar", "pop_hyb"]].sum()
