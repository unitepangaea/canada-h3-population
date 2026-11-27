# =============================================================================
# 03_map_city_resolutions.R
# The same city window at resolutions 6, 7 and 8, with shared density classes.
# =============================================================================
source("R/00_setup.R")

ottawa_bbox <- c(-75.95, 45.25, -75.45, 45.55)

layers <- lapply(c(6, 7, 8), function(r) {
  x <- read_hex("hyb", res = r, bbox = ottawa_bbox)
  x$res_label <- paste("Resolution", r)
  x[, c("h3", "population", "pop_density_km2", "res_label")]
})
city <- do.call(rbind, layers) |>
  add_density_class() |>
  sf::st_transform(CRS_LAMBERT)

# Totals differ slightly between panels only because edge cells overlap the window
city |>
  sf::st_drop_geometry() |>
  dplyr::group_by(res_label) |>
  dplyr::summarise(cells = dplyr::n(), population = round(sum(population)))

p <- ggplot(city) +
  geom_sf(aes(fill = density_class), colour = NA) +
  facet_wrap(~ res_label, nrow = 1) +
  scale_fill_viridis_d(option = "magma", direction = -1,
                       name = "Persons per km\u00b2", drop = FALSE) +
  labs(title = "Ottawa\u2013Gatineau at three H3 resolutions (hybrid layer)") +
  theme_void(base_size = 11) +
  theme(legend.position = "bottom")

ggsave(file.path(FIG_DIR, "ottawa_hyb_res678.png"), p,
       width = 12, height = 5, dpi = 300, bg = "white")
