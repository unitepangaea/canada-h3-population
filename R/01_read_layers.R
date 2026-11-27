# =============================================================================
# 01_read_layers.R
# Reading the layers: GeoPackage, GeoPackage window, and Parquet.
# =============================================================================
source("R/00_setup.R")

# ---- 1. Whole layer (practical for resolutions 6 and 7) ----------------------
hyb6 <- read_hex("hyb", res = 6)
hyb6
summary(hyb6$population)
sum(hyb6$population)   # 36,991,971: every layer conserves the national total

# ---- 2. A window of the resolution 8 layer -----------------------------------
# Reading only the cells in a bounding box avoids loading 2.7 million polygons.
ottawa_bbox <- c(-75.80, 45.35, -75.60, 45.47)   # lon/lat: xmin, ymin, xmax, ymax
hyb8_ott <- read_hex("hyb", res = 8, bbox = ottawa_bbox)
nrow(hyb8_ott)

# ---- 3. Parquet: attributes only, fast to read --------------------------------
hyb8_tab <- read_hex_parquet("hyb", res = 8)
hyb8_tab |>
  dplyr::summarise(cells = dplyr::n(),
                   population = sum(population),
                   median_density = median(pop_density_km2),
                   share_low_count = mean(low_count_flag))

# Build polygons for a subset only, from the H3 index
toronto_cell <- "882b9bc711fffff"   # case-study cell in the paper
nbrs <- h3jsr::get_disk(toronto_cell, ring_size = 3)[[1]]
tor <- hyb8_tab |>
  dplyr::filter(h3 %in% nbrs)
tor <- sf::st_sf(tor, geometry = h3jsr::cell_to_polygon(tor$h3, simple = TRUE))
plot(tor["pop_density_km2"])

# ---- 4. Block-level tables ---------------------------------------------------
db   <- arrow::read_parquet(file.path(DATA_DIR, "db_table_v2.parquet"))
cont <- arrow::read_parquet(file.path(DATA_DIR, "contributions_v2_res8.parquet"))

# Which blocks contribute to the Toronto case-study cell, and from which source?
cont |>
  dplyr::filter(h3 == toronto_cell) |>
  dplyr::left_join(dplyr::select(db, DBUID, pop, source_tau50, vintage_flag),
                   by = "DBUID") |>
  dplyr::arrange(dplyr::desc(pop_hyb))
