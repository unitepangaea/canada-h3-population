# R examples

Run from the repository root. `00_setup.R` installs and loads the required packages (sf, dplyr, ggplot2, arrow, h3jsr, scales) and defines the helper functions used by the other scripts.

| Script | Shows how to |
|---|---|
| `00_setup.R` | Load packages; read a layer whole, by bounding box, or from Parquet; download and verify files |
| `01_read_layers.R` | Read each format, summarise a layer, build hexagons from the H3 index, and query the block-level tables |
| `02_map_national.R` | Map the resolution 6 hybrid layer for Canada |
| `03_map_city_resolutions.R` | Map one city at resolutions 6, 7 and 8 with shared density classes |
| `04_compare_methods.R` | Compare the PHH and NAR layers and map where the hybrid layer uses PHH |
| `05_link_by_h3.R` | Compute catchment populations, population-weighted exposure and the population of user-supplied polygons |

Before downloading the national files, the scripts can be tried on `data/sample/`, which holds the resolution 8 hybrid layer for a window of Ottawa. Point `read_hex()` at that file, or copy it into `data/` with the release file name.
