"""Comparison metrics (Eqs. 13 to 20), ported from 01_final_pipeline/robust_comparison_metrics.py.

Cell sets, as in the preprint code:
  union  H  = cells populated in either layer   (D, Bland-Altman, MARD, Table 3)
  both   H∩ = cells populated in both layers    (Pearson r, r on log1p, Spearman rho)
P for D/P is the mean of the two layer totals (preprint definition).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def pair_frame(a: pd.Series, b: pd.Series) -> pd.DataFrame:
    """Align two cell -> population series on the union of populated cells (a = x, b = y)."""
    df = pd.concat({"x": a[a > 0], "y": b[b > 0]}, axis=1).fillna(0.0)
    return df


def displaced(df: pd.DataFrame) -> dict:
    delta = df.y - df.x
    D = 0.5 * delta.abs().sum()
    P = (df.x.sum() + df.y.sum()) / 2
    return {"D": D, "P": P, "D_over_P": D / P, "total_x": df.x.sum(), "total_y": df.y.sum()}


def correlations(df: pd.DataFrame) -> dict:
    both = df[(df.x > 0) & (df.y > 0)]
    return {
        "n_both": len(both),
        "pearson_r": stats.pearsonr(both.x, both.y)[0],
        "pearson_r_log1p": stats.pearsonr(np.log1p(both.x), np.log1p(both.y))[0],
        "spearman_rho": stats.spearmanr(both.x, both.y)[0],
    }


def bland_altman(df: pd.DataFrame) -> dict:
    diff = df.y - df.x
    bias, sd = diff.mean(), diff.std()          # ddof = 1, as pandas default in the preprint
    return {"ba_bias": bias, "ba_sd": sd, "ba_loa_lower": bias - 1.96 * sd, "ba_loa_upper": bias + 1.96 * sd}


def mard(df: pd.DataFrame, min_pop: float = 0) -> dict:
    m = (df.x + df.y) / 2
    keep = m >= min_pop if min_pop > 0 else pd.Series(True, index=df.index)
    rel = (df.y - df.x).abs()[keep] / m[keep].replace(0, np.nan)
    return {f"mard_min{min_pop:g}": rel.median(), f"n_mard_min{min_pop:g}": int(keep.sum())}


def table3_fixed(df: pd.DataFrame, cuts=(5, 25, 100)) -> pd.DataFrame:
    """Preprint Table 3 (corrected): fixed absolute thresholds; nar_only / phh_only separate.

    x = PHH, y = NAR. pct_of_population uses the mean of the two estimates per cell over a
    single national denominator.
    """
    d = (df.y - df.x).abs()
    cat = np.select(
        [df.x == 0, df.y == 0, d < cuts[0], d < cuts[1], d < cuts[2]],
        ["nar_only", "phh_only", "match", "minor", "moderate"], default="major")
    m = (df.x + df.y) / 2
    t = pd.DataFrame({"agreement": cat, "mean_pop": m}).groupby("agreement").agg(
        n_hexes=("mean_pop", "size"), pop_represented=("mean_pop", "sum"))
    t["pct_of_hexes"] = (t.n_hexes / len(df) * 100).round(1)
    t["pct_of_population"] = (t.pop_represented / m.sum() * 100).round(1)
    return t.reset_index()


def core_metrics(a: pd.Series, b: pd.Series) -> dict:
    df = pair_frame(a, b)
    out = {"n_union": len(df)}
    out |= displaced(df) | correlations(df) | bland_altman(df) | mard(df, 0) | mard(df, 5)
    return out
