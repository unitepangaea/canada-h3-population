"""B3 unit tests on a small synthetic DB set (protocol Section 4).

  - per-DB conservation is exact for each method and resolution
  - s(d) is identical across r
  - known points land in known cells
  - the tier-2 fallback triggers on a sliver polygon
"""
from __future__ import annotations

import sys
from pathlib import Path

import h3
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hexpop import core  # noqa: E402

RES = [6, 7, 8]
TAU = 50
TOL = 1e-9

# Synthetic DBs near downtown Toronto (lon, lat boxes)
POLYS = {
    "A": box(-79.400, 43.640, -79.370, 43.670),          # well covered by NAR
    "B": box(-79.300, 43.700, -79.260, 43.730),          # zero NAR coverage, large: tier 1 at r = 8
    "C": box(-79.5000, 43.6000, -79.49999, 43.6010),     # sliver (~1 m wide): tier 2 at every r
    "D": box(-79.450, 43.650, -79.440, 43.660),          # zero population, has NAR points
    "E": box(-79.420, 43.680, -79.410, 43.690),          # thin coverage: 1000 people, 2 locations
}
POP = pd.Series({"A": 100.0, "B": 50.0, "C": 7.0, "D": 0.0, "E": 1000.0})


def _pts_in(b, k, seed):
    rng = np.random.default_rng(seed)
    minx, miny, maxx, maxy = b.bounds
    return rng.uniform(miny, maxy, k), rng.uniform(minx, maxx, k)


@pytest.fixture(scope="module")
def synth():
    # PHH points: every populated DB has points summing exactly to POP (as verified in A2)
    phh_rows = []
    for i, (d, k) in enumerate({"A": 7, "B": 4, "C": 1, "E": 9, "D": 2}.items()):
        lat, lon = _pts_in(POLYS[d], k, i)
        w = np.random.default_rng(100 + i).uniform(0.1, 1, k)
        pops = POP[d] * w / w.sum()
        phh_rows += [(d, la, lo, p) for la, lo, p in zip(lat, lon, pops)]
    phh = pd.DataFrame(phh_rows, columns=["DBUID", "lat", "lon", "pop"])

    # NAR locations: assigned to DBs by point-in-polygon, plus two outside every DB
    nar_rows = []
    for i, (d, k) in enumerate({"A": 23, "D": 5, "E": 2}.items()):
        lat, lon = _pts_in(POLYS[d], k, 50 + i)
        nar_rows += list(zip(lat, lon))
    nar_rows += [(43.80, -79.10), (43.55, -79.60)]
    nar = pd.DataFrame(nar_rows, columns=["lat", "lon"])
    ids = np.array(list(POLYS))
    idx, n_multi = core.points_in_polygons(nar.lon.to_numpy(), nar.lat.to_numpy(), list(POLYS.values()))
    nar["DBUID"] = np.where(idx >= 0, ids[np.clip(idx, 0, None)], None)
    assert n_multi == 0
    nar = nar[nar.DBUID.notna()]
    n = nar.groupby("DBUID").size().reindex(POP.index).fillna(0)
    source = core.source_assignment(POP, n, TAU)
    zero = POP.index[(POP > 0) & (n == 0)]
    geoms = pd.Series({d: POLYS[d] for d in zero})

    runs = {}
    for r in RES:
        phh_cells = core.tag_cells(phh.lat, phh.lon, r)
        nar_cells = core.tag_cells(nar.lat, nar.lon, r)
        lt, fb, un = core.build_contributions(POP, source, geoms, phh.DBUID.to_numpy(), phh["pop"].to_numpy(),
                                              phh_cells, nar.DBUID.to_numpy(), nar_cells, r)
        runs[r] = dict(lt=lt, fb=fb, un=un, n=n, source=source)
    return dict(phh=phh, nar=nar, n=n, runs=runs)


def test_points_in_polygons_assigns_and_drops(synth):
    nar = synth["nar"]
    assert len(nar) == 23 + 5 + 2                      # the two outside points are unassigned
    assert synth["n"].to_dict() == {"A": 23, "B": 0, "C": 0, "D": 5, "E": 2}


def test_source_assignment_rules(synth):
    s = synth["runs"][8]["source"]
    assert s.to_dict() == {"A": "NAR", "B": "PHH", "C": "PHH", "D": "n/a", "E": "PHH"}
    # thin coverage is strict: c = tau stays NAR
    assert core.source_assignment(pd.Series([100.0]), pd.Series([2]), 50).iloc[0] == "NAR"
    assert core.source_assignment(pd.Series([101.0]), pd.Series([2]), 50).iloc[0] == "PHH"


@pytest.mark.parametrize("r", RES)
@pytest.mark.parametrize("method", ["phh", "nar", "hyb"])
def test_per_db_conservation(synth, r, method):
    lt = synth["runs"][r]["lt"]
    assert synth["runs"][r]["un"].empty
    tot = core.db_totals(lt)[f"pop_{method}"].reindex(POP.index).fillna(0.0)
    assert np.abs(tot - POP).max() < TOL
    assert abs(lt[f"pop_{method}"].sum() - POP.sum()) < TOL


def test_source_identical_across_resolutions(synth):
    runs = synth["runs"]
    base = runs[RES[0]]
    for r in RES[1:]:
        pd.testing.assert_series_equal(runs[r]["source"], base["source"])
        a = core.db_totals(runs[r]["lt"]).reindex(POP.index).fillna(0.0)
        b = core.db_totals(base["lt"]).reindex(POP.index).fillna(0.0)
        assert np.abs(a - b).to_numpy().max() < TOL


def test_hybrid_never_uses_fallback(synth):
    for r in RES:
        lt = synth["runs"][r]["lt"]
        used = lt[(lt.pop_hyb > 0) & (lt.src_hyb == "NAR")]
        assert (used.nar_tier == 0).all()
        phh_src = lt[lt.src_hyb == "PHH"]
        assert np.allclose(phh_src.pop_hyb, phh_src.pop_phh)


@pytest.mark.parametrize("cell", ["882b9bc711fffff", "872b9bc71ffffff", "862b9bc77ffffff"])
def test_known_points_land_in_known_cells(cell):
    r = h3.get_resolution(cell)
    lat, lon = h3.cell_to_latlng(cell)
    got = core.tag_cells([lat], [lon], r)
    assert core.cells_to_str(got) == [cell]
    assert h3.int_to_str(int(got[0])) == cell


def test_toronto_parents():
    assert h3.cell_to_parent("882b9bc711fffff", 7) == "872b9bc71ffffff"
    assert h3.cell_to_parent("882b9bc711fffff", 6) == "862b9bc77ffffff"


@pytest.mark.parametrize("r", RES)
def test_tier2_fallback_on_sliver(r):
    fb, un = core.areal_fallback(pd.Series({"C": POLYS["C"]}), POP, r)
    assert un.empty
    assert len(fb) == 1 and fb.nar_tier.iloc[0] == 2
    assert fb.pop_nar.iloc[0] == pytest.approx(POP["C"])
    p = POLYS["C"].representative_point()
    assert fb.h3.iloc[0] == core.tag_cells([p.y], [p.x], r)[0]


def test_tier1_fallback_on_large_polygon(synth):
    fb = synth["runs"][8]["fb"]
    b = fb[fb.DBUID == "B"]
    assert (b.nar_tier == 1).all() and len(b) > 1
    assert b.pop_nar.sum() == pytest.approx(POP["B"])


def test_hex_table_columns(synth):
    lt = synth["runs"][8]["lt"]
    hyb = core.hex_table(lt, "hyb", 8, 5)
    nar = core.hex_table(lt, "nar", 8, 5)
    assert {"h3", "res", "population", "n_dbs_contributing", "share_pop_from_phh_source", "low_count_flag"} <= set(hyb)
    assert "fallback_tier" in nar
    assert hyb.population.sum() == pytest.approx(POP.sum())
    assert hyb.share_pop_from_phh_source.between(0, 1).all()
    assert (hyb.low_count_flag == (hyb.population < 5)).all()


def test_tau_sweep_counts():
    sw = core.tau_sweep(POP, pd.Series({"A": 23, "B": 0, "C": 0, "D": 5, "E": 2}), [5, 50, 1000])
    assert sw.n_zero_coverage_dbs.tolist() == [2, 2, 2]
    assert sw.n_thin_coverage_dbs.tolist() == [1, 1, 0]   # A: 100/23 = 4.3 < 5; E: 500
