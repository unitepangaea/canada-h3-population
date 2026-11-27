"""
build_release.py

Assemble the release files from the pipeline outputs:

  1. Copy each hexagon layer into release/ with the public file name,
     writing a GeoPackage in EPSG:4326 and a Parquet file without geometry.
  2. Copy the block table and contribution tables.
  3. Write SHA256SUMS and data/MANIFEST.csv (rows, population total, size, hash).
  4. Write a small sample extract to data/sample/ for the R examples.

Usage (from the repository root):

    python scripts/build_release.py --pipeline-out /path/to/output_v2/v2 --version v2

The --pipeline-out folder is expected to contain res6/, res7/ and res8/
sub-folders. Edit SOURCE_PATTERNS below if the pipeline file names differ.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from pathlib import Path

import geopandas as gpd
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RELEASE_DIR = REPO / "release"
DATA_DIR = REPO / "data"
SAMPLE_DIR = DATA_DIR / "sample"

LAYERS = ["hyb", "phh", "nar", "hybv"]
RESOLUTIONS = [6, 7, 8]
NATIONAL_POP = 36_991_971
TOL = 1e-3  # persons, for the national total after floating-point summation

# Pipeline outputs, as written by 03_allocate.py (method v2, tau = 50).
# {out} is <pipeline-out> (output_v2/v2) and {r} the resolution. The HYB-V
# sensitivity layer is written to the sibling folder output_v2/v2_hybv/.
# Each res folder also holds *_albers_equal_area, *_nad83_geographic and
# *_statcan_lambert copies of the hybrid layer; only the EPSG:4326 file is used.
SOURCE_PATTERNS = {
    "hyb": "{out}/res{r}/hyb_h3_res{r}.gpkg",
    "phh": "{out}/res{r}/phh_h3_res{r}.gpkg",
    "nar": "{out}/res{r}/nar_h3_res{r}.gpkg",
    "hybv": "{out}_hybv/res{r}/hyb_h3_res{r}.gpkg",
}
DB_TABLE_PATTERN = "db_table.parquet"
CONTRIB_PATTERN = "contrib_long.parquet"

# Sample window (Ottawa), longitude/latitude
SAMPLE_BBOX = (-75.80, 45.35, -75.60, 45.47)


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def find_one(folder: Path, pattern: str) -> Path:
    hits = sorted(folder.glob(pattern))
    if len(hits) != 1:
        raise FileNotFoundError(
            f"Expected one file matching {pattern!r} in {folder}, found {len(hits)}: "
            f"{[h.name for h in hits]}. Edit SOURCE_PATTERNS in build_release.py."
        )
    return hits[0]


def release_hex_layer(src: Path, layer: str, res: int, version: str) -> list[dict]:
    gdf = gpd.read_file(src)
    if gdf.crs is None:
        raise ValueError(f"{src} has no CRS")
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)

    total = float(gdf["population"].sum())
    if abs(total - NATIONAL_POP) > TOL:
        raise ValueError(f"{src.name}: national total {total:,.3f} != {NATIONAL_POP:,}")
    if gdf["h3"].duplicated().any():
        raise ValueError(f"{src.name}: duplicate H3 cells")

    stem = f"hexpop_{layer}_{version}_res{res}"
    gpkg = RELEASE_DIR / f"{stem}.gpkg"
    pq = RELEASE_DIR / f"{stem}.parquet"
    gdf.to_file(gpkg, layer=stem, driver="GPKG")
    pd.DataFrame(gdf.drop(columns="geometry")).to_parquet(pq, index=False)

    meta = dict(layer=layer, version=version, res=res, rows=len(gdf),
                population_total=round(total, 3))
    if layer == "hyb" and res == 8:
        write_sample(gdf, stem)
    return [dict(file=gpkg.name, format="gpkg", **meta),
            dict(file=pq.name, format="parquet", **meta)]


def write_sample(gdf: gpd.GeoDataFrame, stem: str) -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    xmin, ymin, xmax, ymax = SAMPLE_BBOX
    sample = gdf.cx[xmin:xmax, ymin:ymax]
    out = SAMPLE_DIR / f"{stem}_ottawa_sample.gpkg"
    sample.to_file(out, layer=out.stem, driver="GPKG")
    print(f"  sample: {len(sample):,} cells -> {out.relative_to(REPO)}")


def release_table(src: Path, dest_name: str, version: str, res: int | str = "") -> dict:
    dest = RELEASE_DIR / dest_name
    shutil.copy2(src, dest)
    df = pd.read_parquet(dest)
    # Block table: POP (from the GAF); contribution tables: pop_hyb
    pop_col = next((c for c in ("POP", "pop", "pop_hyb") if c in df.columns), None)
    total = round(float(df[pop_col].sum()), 3) if pop_col else ""
    return dict(file=dest_name, layer="table", version=version, res=res,
                format="parquet", rows=len(df), population_total=total)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline-out", required=True, type=Path)
    ap.add_argument("--version", default="v2")
    args = ap.parse_args()

    RELEASE_DIR.mkdir(exist_ok=True)
    rows: list[dict] = []

    for res in RESOLUTIONS:
        folder = args.pipeline_out / f"res{res}"
        for layer in LAYERS:
            target = Path(SOURCE_PATTERNS[layer].format(out=args.pipeline_out, r=res))
            src = find_one(target.parent, target.name)
            print(f"res {res} {layer}: {src.name}")
            rows += release_hex_layer(src, layer, res, args.version)
        src = find_one(folder, CONTRIB_PATTERN)
        rows.append(release_table(src, f"contributions_{args.version}_res{res}.parquet",
                                  args.version, res))

    src = find_one(args.pipeline_out, DB_TABLE_PATTERN)
    rows.append(release_table(src, f"db_table_{args.version}.parquet", args.version))

    # Checksums and manifest
    with open(RELEASE_DIR / "SHA256SUMS", "w") as f:
        for r in rows:
            p = RELEASE_DIR / r["file"]
            r["bytes"] = p.stat().st_size
            r["sha256"] = sha256(p)
            f.write(f"{r['sha256']}  {r['file']}\n")

    fields = ["file", "layer", "version", "res", "format", "rows",
              "population_total", "bytes", "sha256"]
    with open(DATA_DIR / "MANIFEST.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    shutil.copy2(RELEASE_DIR / "SHA256SUMS", DATA_DIR / "SHA256SUMS")

    big = [r for r in rows if r["bytes"] > 50e9]
    print(f"\n{len(rows)} files written to {RELEASE_DIR.relative_to(REPO)}/ "
          f"({sum(r['bytes'] for r in rows) / 1e9:.2f} GB in total)")
    if big:
        print("WARNING: files above Zenodo's 50 GB per-record limit:", [r["file"] for r in big])


if __name__ == "__main__":
    main()
