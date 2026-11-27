# Hexagonal Population Surfaces for Canada (H3 Resolutions 6, 7 and 8)

Open, national population count and density surfaces for Canada on the Uber H3 hexagonal grid, produced by disaggregating 2021 Census Dissemination Block (DB) population with a hybrid dasymetric method. The repository holds the source code that builds the surfaces, documentation for every data layer, example R code for reading and mapping the layers, and the preprint that describes the method.

> McGaughey, T. and Peters, P.A. (2026). *A Hybrid Dasymetric Method for Hexagonal Population Density Mapping in Canada: Reconciling Road-Based and Address-Based Allocation at National Scale.* Preprints.org. https://doi.org/10.20944/preprints202609.2636.v1

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)

---

## What is in this repository

| Folder | Contents |
|---|---|
| `data/` | Download instructions, file manifest with checksums, and a small sample extract. The full national layers are archived on Zenodo because they exceed GitHub file limits. |
| `docs/` | Data dictionary, methods summary, data provenance and licences, and fitness-for-use guidance by resolution. |
| `src/` | Python pipeline that builds every layer from the open source data. |
| `R/` | Example R scripts for reading, mapping and linking the layers. |
| `paper/` | The preprint (PDF) and its citation. |

## The data layers

Each layer is provided at three H3 resolutions, so that the spatial unit can be matched to the scale of the analysis.

| Resolution | Mean cell area | Mean edge (H3 v4) | Suggested scale |
|---|---|---|---|
| 6 | 36.13 km² | 3.73 km | Regional, rural and northern, national display |
| 7 | 5.16 km² | 1.41 km | Community, small town, rural service area |
| 8 | 0.74 km² | 0.53 km | Neighbourhood |

| Layer | Method | Recommended for |
|---|---|---|
| `hyb` | Hybrid: National Address Register (NAR) allocation, with Pseudo-Household (PHH) allocation where address coverage is absent or thin (τ = 50 persons per location) | **General use (headline layer)** |
| `phh` | Road-based allocation from ISED Pseudo-Household points | Method comparison and sensitivity analysis |
| `nar` | Address-based allocation from NAR residential locations, with an areal fallback | Method comparison and sensitivity analysis |

Every layer conserves the published 2021 DB population exactly (national total 36,991,971). Column definitions are in [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md).

## Quick start (R)

```r
# 1. Download the layers from Zenodo into data/ (see data/README.md)
# 2. Read the resolution 7 hybrid layer and map it
library(sf)
library(ggplot2)

hex <- st_read("data/hexpop_hyb_v2_res7.gpkg")

ggplot(hex) +
  geom_sf(aes(fill = pop_density_km2), colour = NA) +
  scale_fill_viridis_c(trans = "log10", name = "Persons per km²") +
  theme_void()
```

Further examples, including city windows, multi-resolution comparison and linkage to other data by H3 index, are in [`R/`](R/).

## Rebuilding the layers (Python)

The pipeline in `src/` rebuilds every layer from the open source data. Instructions, the pinned environment and the expected run times are in [`src/README.md`](src/README.md).

## Before you use the layers

Please read [`docs/FITNESS_FOR_USE.md`](docs/FITNESS_FOR_USE.md). In brief:

1. The surfaces are modelled estimates. Cell values below the DB level are allocations, not counts.
2. H3 cells do not nest exactly inside their parents. Aggregating the resolution 8 layer to resolution 7 or 6 gives slightly different values from the directly built coarser layers, so use the provided layer for each resolution.
3. The population is from the 2021 Census and the address register is from 2026, so areas of post-2021 growth may be misallocated within their DB.
4. Very small cell counts are common at resolution 8 in rural and northern areas. Use a coarser resolution for rates.

## Citation

Please cite both the data and the paper. Citation metadata are in [`CITATION.cff`](CITATION.cff), and GitHub's "Cite this repository" button reads them.

## Licences

- **Code** (`src/`, `R/`): MIT License, see [`LICENSE`](LICENSE).
- **Data layers and documentation**: Creative Commons Attribution 4.0 International (CC BY 4.0), see [`LICENSE-DATA.md`](LICENSE-DATA.md). The layers are derived from data published by Statistics Canada and Innovation, Science and Economic Development Canada under the Open Government Licence – Canada and the Statistics Canada Open Licence; the required attribution statements are in [`docs/PROVENANCE.md`](docs/PROVENANCE.md).
- **Preprint**: under the licence stated by Preprints.org.

This product is not endorsed by Statistics Canada or Innovation, Science and Economic Development Canada.

## Contact

Paul A. Peters, Spatial and Social Determinants of Health Lab, Carleton University, Ottawa, Canada.
Lab website: https://carleton.ca/determinants/

Questions and error reports are welcome through [GitHub Issues](../../issues).
