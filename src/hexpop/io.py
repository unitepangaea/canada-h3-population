"""Shared loaders and logging for the numbered scripts."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402


class Log:
    """Print and keep lines; write to a file at the end."""

    def __init__(self, path: Path):
        self.path = path
        self.lines: list[str] = []
        self.t0 = time.time()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(f"# {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    def __call__(self, msg: str) -> None:
        line = f"[{time.time() - self.t0:7.0f}s] {msg}"
        print(line, flush=True)
        self.lines.append(line)
        with open(self.path, "a") as f:
            f.write(line + "\n")

    def save(self) -> None:
        """Kept for compatibility; lines are written as they are logged."""


def load_gaf() -> pd.DataFrame:
    gaf = pd.read_csv(C.GAF_CSV, usecols=list(C.GAF_COLS), dtype=str, encoding="latin1")
    gaf = gaf.rename(columns=C.GAF_COLS)
    gaf["POP"] = pd.to_numeric(gaf["POP"], errors="coerce").fillna(0.0)
    gaf["DB_TDWELL"] = pd.to_numeric(gaf["DB_TDWELL"], errors="coerce").fillna(0.0)
    gaf["DB_LANDAREA_KM2"] = pd.to_numeric(gaf["DB_LANDAREA_KM2"], errors="coerce")
    return gaf


def load_db_polygons(shp: Path) -> gpd.GeoDataFrame:
    """DB polygons in EPSG:4326 with make_valid, as in the preprint code."""
    dbs = gpd.read_file(shp, columns=[C.DB_SHP_DBUID_COL])
    dbs = dbs.rename(columns={C.DB_SHP_DBUID_COL: "DBUID"})
    dbs["DBUID"] = dbs["DBUID"].astype(str)
    dbs = dbs.to_crs(4326)
    dbs["geometry"] = dbs["geometry"].make_valid()
    return dbs


def universe_dbuids() -> pd.Index:
    """DBs with a polygon in the cartographic file (decision 2026-11-06)."""
    return pd.Index(pd.read_parquet(C.DB_CARTO_4326, columns=["DBUID"])["DBUID"])
