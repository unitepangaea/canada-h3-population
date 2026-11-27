# Pipeline source code

The Python pipeline rebuilds every released layer from the open source data listed in `docs/PROVENANCE.md`.

## Environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r src/requirements.txt
```

H3 version 4 or later is required. The versions used for each release, including GEOS and PROJ, are recorded in `src/ENVIRONMENT.md`.

## Input data

Download the inputs listed in `docs/PROVENANCE.md` and unpack them into `data_raw/` at the repository root, with this layout:

```
data_raw/
  GAF2021.csv                       Geographic Attribute File
  ldb_000a21a_e/ldb_000a21a_e.shp   Dissemination Block digital boundary file
  ldb_000b21a_e/ldb_000b21a_e.shp   Dissemination Block cartographic boundary file
  lda_000b21a_e/lda_000b21a_e.shp   Dissemination Area cartographic boundary file (04_validate.py, V6)
  phh_2021/PHH_2021_CSV/PHH-*.csv   Pseudo-Household Demographic Distribution
  NAR-202606/                       National Address Register (Locations/ and Addresses/)
  province_boundaries.gpkg          Province and territory polygons (07_figures.py only)
  reference_v1/                     Preprint outputs (c_reproduce_preprint.py only)
```

The National Address Register Addresses files are about 4 GB. Every path in `src/config.py` is relative to the repository root, so no paths need to be edited. The pipeline writes to `data_int/`, `output_v2/`, `tables/` and `figures/` at the root, all of which are excluded from git.

To keep inputs or outputs in another location, for example on an external drive, copy `src/config_local_example.py` to `src/config_local.py` and set the folders there. `config_local.py` is excluded from git.

## Running

```bash
# Reproduce the preprint (method v1, resolution 8)
python src/run_all.py --method v1 --res 8 --variant base

# Build the released layers (method v2, all resolutions)
python src/run_all.py --method v2 --res 6 7 8 --variant base hybv --crs-variants

# Unit tests
pytest src/tests
```

Run time for the full v2 build is about 2 to 4 hours on a recent laptop with 16 GB of memory, most of it in the address-file join and in point binning at three resolutions.

## Modules

| Script | Purpose |
|---|---|
| `config.py` | Paths, resolutions, τ values, method switches and CRS |
| `01_prepare_points.py` | Prepares PHH points and NAR residential locations, assigns NAR locations to blocks and tags all points with H3 cells at each resolution |
| `02_db_table.py` | Builds the block table: population, location counts, vintage check and the source assigned at each τ |
| `03_allocate.py` | Allocates block population to cells for PHH, NAR and hybrid at a given resolution, and writes the contribution table and hexagon layers |
| `04_validate.py` | Conservation, cross-resolution invariance, non-nesting and fallback checks |
| `05_compare.py` | Method comparison metrics |
| `06_case_study.py` | Toronto case study and national re-ranking |
| `07_figures.py`, `08_tables.py` | Figures and tables for the paper; `08_tables.py` writes every value reported in the manuscript with its source file |
| `run_all.py` | Command-line entry point |
| `tests/` | Unit tests on a small synthetic block set |
