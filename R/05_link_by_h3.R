# =============================================================================
# 05_link_by_h3.R
# Using the H3 index to link the population layer to other data.
#   A. Population within a ring of cells around facilities (simple catchment)
#   B. Population-weighted mean of a cell-level exposure
#   C. Population of user-supplied polygons
# =============================================================================
source("R/00_setup.R")

res <- 8
hyb <- read_hex_parquet("hyb", res) |> dplyr::select(h3, population)

# ---- A. Catchment population around points -----------------------------------
# Example points (replace with clinics, schools, pharmacies, etc.)
sites <- data.frame(
  site = c("Parliament Hill", "Carleton University"),
  lon  = c(-75.7009, -75.6972),
  lat  = c(45.4236,  45.3876)
) |>
  sf::st_as_sf(coords = c("lon", "lat"), crs = 4326)

sites$h3 <- h3jsr::point_to_cell(sites, res = res)

# A disk of k rings at resolution 8 spans roughly (2k + 1) x 0.9 km across
k <- 2
catch <- lapply(seq_len(nrow(sites)), function(i) {
  data.frame(site = sites$site[i],
             h3 = h3jsr::get_disk(sites$h3[i], ring_size = k)[[1]])
}) |>
  dplyr::bind_rows() |>
  dplyr::left_join(hyb, by = "h3") |>
  dplyr::group_by(site) |>
  dplyr::summarise(cells = dplyr::n(),
                   population = sum(population, na.rm = TRUE))
catch

# ---- B. Population-weighted exposure -------------------------------------------
# 'exposure' stands in for any surface already summarised to H3 cells
# (for example, annual PM2.5 or heat days).
set.seed(1)
exposure <- data.frame(h3 = hyb$h3, value = rlnorm(nrow(hyb), log(7), 0.3))

hyb |>
  dplyr::inner_join(exposure, by = "h3") |>
  dplyr::summarise(pop_weighted_mean = weighted.mean(value, population),
                   unweighted_mean   = mean(value))

# For exposure surfaces held at a different resolution, move between
# resolutions with h3jsr::get_parent() or h3jsr::get_children().

# ---- C. Population of user-supplied polygons -----------------------------------
# Assign each cell to the polygon containing its centre, then sum. Cell-centre
# assignment is adequate when polygons are much larger than cells; otherwise,
# use a finer resolution.
zone_pop <- function(zones, hex_tab) {
  zones <- sf::st_transform(zones, 4326)
  pts <- sf::st_sf(hex_tab, geometry = h3jsr::cell_to_point(hex_tab$h3, simple = TRUE))
  joined <- sf::st_join(pts, zones, join = sf::st_within)
  sf::st_drop_geometry(joined)
}
# Example with your own polygons (for example, health regions):
# my_regions <- sf::st_read("my_regions.gpkg")
# zone_pop(my_regions, hyb) |>
#   dplyr::group_by(region_id) |>
#   dplyr::summarise(population = sum(population))
