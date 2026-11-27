# Data

The national layers are archived on Zenodo, which assigns a DOI to each release, and are not stored in this repository because several files exceed GitHub's 100 MB file limit.

**Zenodo record:** https://doi.org/10.5281/zenodo.24592692 (concept DOI, which always resolves to the latest version)

## Download

1. Download the files you need from the Zenodo record into this folder. The Parquet files are the smallest; the GeoPackage files include hexagon polygons.
2. Check the files against `MANIFEST.csv`:

   ```r
   source("R/00_setup.R")
   check_manifest("data")
   ```

   or, from a terminal: `shasum -a 256 -c data/SHA256SUMS`

Alternatively, `R/00_setup.R` provides `download_layer()`, which downloads a named file from the Zenodo record and checks its checksum.

## Contents of the Zenodo record

| File pattern | Count | Description |
|---|---|---|
| `hexpop_<layer>_v2_res<r>.gpkg` | 12 | Hexagon layers with polygons (4 layers × 3 resolutions) |
| `hexpop_<layer>_v2_res<r>.parquet` | 12 | Hexagon layers, H3 index only |
| `db_table_v2.parquet` | 1 | Block-level inputs and source assignment |
| `contributions_v2_res<r>.parquet` | 3 | Block-to-cell allocation for each resolution |
| `SHA256SUMS` | 1 | Checksums |

Column definitions are in `docs/DATA_DICTIONARY.md`.

## Sample data

`sample/` holds the resolution 8 hybrid layer for a small window of Ottawa, small enough to keep in the repository, so that the R examples can be run before downloading the national files.
