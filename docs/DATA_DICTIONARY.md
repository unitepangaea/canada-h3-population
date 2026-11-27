# Data dictionary

<!-- MAINTAINER: every column name and value range below must be checked against the released files before tagging a release. Run scripts/check_release.py, which compares this file against the parquet schemas. -->

## 1. File naming

```
hexpop_<layer>_<version>_res<r>.<ext>
```

| Part | Values | Meaning |
|---|---|---|
| `layer` | `hyb`, `phh`, `nar`, `hybv` | Allocation method (Section 3) |
| `version` | `v1`, `v2` | Method version (see `CHANGELOG.md`) |
| `r` | `6`, `7`, `8` | H3 resolution |
| `ext` | `gpkg`, `parquet` | GeoPackage with hexagon polygons, or Parquet with the H3 index only |

Example: `hexpop_hyb_v2_res7.gpkg` is the hybrid layer, method version 2, at H3 resolution 7.

Two block-level tables accompany the hexagon layers:

| File | Contents |
|---|---|
| `db_table_v2.parquet` | One row per Dissemination Block in the 2021 cartographic boundary file (498,547 blocks, of which 384,284 are populated), with the inputs to the hybrid rule and the source assigned to each block |
| `contributions_v2_res<r>.parquet` | One row per block–cell pair, with the population each method allocates from that block to that cell |

## 2. Formats and coordinate reference systems

| Format | Geometry | CRS | Notes |
|---|---|---|---|
| GeoPackage (`.gpkg`) | Hexagon polygons | EPSG:4326 (WGS 84, longitude/latitude) | One layer per file. Opens in QGIS, ArcGIS Pro and R (`sf`) |
| Parquet (`.parquet`) | None; the `h3` column is the spatial key | Not applicable | Smallest files. Rebuild polygons with any H3 library (see `R/01_read_layers.R`) |

Cell areas and densities are computed in Canada Albers Equal Area Conic (ESRI:102001) from each cell's own polygon. H3 cells vary in area with latitude, so `area_km2` should be used rather than the nominal mean area.

To reproject for national mapping, Statistics Canada Lambert (EPSG:3347) or Canada Albers (ESRI:102001) are suitable.

## 3. Layers

| Layer | Method | Description |
|---|---|---|
| `hyb` | Hybrid (headline) | Each block is allocated from NAR residential locations unless the block has no NAR location or has more than τ = 50 persons per location, in which case it is allocated from PHH points. The source is assigned once per block and is identical at every resolution |
| `phh` | Pseudo-Household | Block population allocated from ISED Pseudo-Household points, which are placed along road segments |
| `nar` | National Address Register | Block population divided equally among the block's NAR residential locations. Blocks with no location use a two-tier areal fallback on the cartographic block polygon |
| `hybv` | Hybrid, vintage-adjusted (sensitivity) | As `hyb`, except that blocks flagged for probable post-2021 growth (Section 6) are allocated from PHH |

## 4. Hexagon layer columns

| Column | Type | Units | Description |
|---|---|---|---|
| `h3` | string | | H3 cell index (H3 v4, 15-character hexadecimal) |
| `res` | integer | | H3 resolution (6, 7 or 8) |
| `population` | double | persons | Population allocated to the cell. Fractional because block populations are divided among points |
| `area_km2` | double | km² | Cell area in ESRI:102001 |
| `pop_density_km2` | double | persons/km² | `population / area_km2` |
| `n_dbs_contributing` | integer | | Number of Dissemination Blocks contributing population to the cell |
| `share_pop_from_phh_source` | double | 0 to 1 | Hybrid layers only. Share of the cell's population from blocks allocated by PHH |
| `fallback_tier` | integer | | NAR layer only. Highest allocation tier among the blocks contributing to the cell: 0 = NAR location points only; 1 = areal fallback, equal shares to every cell whose centre lies in the cartographic block polygon; 2 = areal fallback, the cell containing the polygon's representative point (Eq. 5) |
| `low_count_flag` | boolean | | TRUE if `population` is below 5 persons (`LOW_COUNT_THRESHOLD` in `src/config.py`). Use with care for rates |

Only cells with population greater than zero are included.

## 5. Block table (`db_table_v2.parquet`)

Geographic codes and names are taken from the 2021 Geographic Attribute File (GAF).

| Column | Type | Description |
|---|---|---|
| `DBUID` | string | 2021 Dissemination Block identifier |
| `PR` | string | Province or territory code |
| `CSDUID`, `CSDNAME` | string | Census subdivision code and name |
| `CMAPUID`, `CMAUID`, `CMANAME` | string | Census metropolitan area or census agglomeration: provincial-part code, code and name |
| `POPCTRRAPUID`, `POPCTRRANAME`, `POPCTRRACLASS` | string | Population centre or rural area: provincial-part code, name and class |
| `DAUID` | string | Dissemination Area code |
| `POP` | double | 2021 block population, POP(d) |
| `DB_TDWELL` | double | 2021 total private dwellings (GAF) |
| `DB_LANDAREA_KM2` | double | Block land area, km² (GAF) |
| `n` | integer | NAR residential locations in the block (building-use classes 1 and 2, digital boundary file), n(d) |
| `n_all` | integer | NAR locations in the block before the building-use filter |
| `c` | double | POP(d) / n(d), persons per location, c(d). Missing when n(d) = 0 |
| `a` | integer | Residential address records at the block's NAR locations, a(d) |
| `w` | double | PHH 2021 total dwellings, w(d) |
| `g` | double | a(d) / w(d), g(d). Missing or infinite when w(d) = 0 |
| `vint_g1.5`, `vint_g1.25`, `vint_g2` | boolean | Probable post-2021 growth at γ = 1.5 (headline), 1.25 and 2: POP(d) > 0, g(d) > γ and a(d) − w(d) ≥ 10. The `hybv` layer reallocates blocks with `vint_g1.5` = TRUE from PHH |
| `zero_cov` | boolean | Zero NAR coverage: POP(d) > 0 and n(d) = 0 |
| `s_tau5` … `s_tau100` | string | Hybrid source under τ = 5, 10, 20, 50 and 100: `"NAR"`, `"PHH"`, or `"n/a"` for blocks with no population |
| `s_final` | string | Source used for the `hyb` layer; equal to `s_tau50` |
| `n_cells_phh_6` … `n_cells_nar_8` | integer | Number of distinct cells at resolution 6, 7 or 8 holding the block's PHH points with population (`phh`) or its active NAR locations (`nar`) |
| `forced_6` … `forced_8` | boolean | TRUE if the block's PHH points and NAR locations each fall in a single cell, and it is the same cell, so that the two methods must agree for this block at that resolution |

## 6. Contribution tables (`contributions_v2_res<r>.parquet`)

| Column | Type | Description |
|---|---|---|
| `DBUID` | string | Dissemination Block |
| `h3` | string | H3 cell at resolution r |
| `pop_phh` | double | Population allocated from the block to the cell under PHH |
| `pop_nar` | double | Population allocated under NAR |
| `nar_tier` | integer | NAR allocation tier for this block–cell pair: 0 = location points, 1 or 2 = areal fallback tier (Section 4), −1 = no NAR contribution |
| `src_hyb` | string | Hybrid source of the block (`s_final`): `"NAR"`, `"PHH"`, or `"n/a"` for blocks with no population |
| `pop_hyb` | double | Population allocated under the hybrid rule: `pop_phh` where `src_hyb` is `"PHH"`, `pop_nar` where it is `"NAR"` |

Summing any `pop_*` column by `h3` reproduces the corresponding hexagon layer, and summing by `DBUID` reproduces the block population. These tables allow users to build their own variants (for example a different τ) without rerunning the pipeline.

## 7. Conservation checks

For every layer and resolution, the release checks confirm that:

1. Block totals are conserved to within 1e-6 persons.
2. Province and territory totals are conserved to within 1e-6 persons.
3. The national total is 36,991,971.

The check results for each release are in `data/MANIFEST.csv` and `docs/validation_v2.md`.
