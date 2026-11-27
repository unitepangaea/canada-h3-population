# =============================================================================
# 02_map_national.R
# National map of the hybrid layer at resolution 6.
# Resolution 6 is recommended for national figures; resolution 8 cells are too
# small to see at this scale.
# =============================================================================
source("R/00_setup.R")

hyb6 <- read_hex("hyb", res = 6) |>
  add_density_class() |>
  sf::st_transform(CRS_LAMBERT)

p <- ggplot(hyb6) +
  geom_sf(aes(fill = density_class), colour = NA) +
  scale_fill_viridis_d(option = "magma", direction = -1,
                       name = "Persons per km\u00b2", drop = FALSE) +
  labs(title = "Population density, H3 resolution 6",
       subtitle = "Hybrid dasymetric allocation of 2021 Census Dissemination Block population",
       caption = paste("Source: McGaughey and Peters (2026). Adapted from Statistics Canada",
                       "and ISED Canada data.")) +
  theme_void(base_size = 11) +
  theme(legend.position = "right")

ggsave(file.path(FIG_DIR, "national_hyb_res6.png"), p,
       width = 9, height = 7, dpi = 300, bg = "white")
