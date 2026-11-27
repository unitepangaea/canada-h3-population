# =============================================================================
# 04_compare_methods.R
# Comparing the PHH and NAR allocations, and mapping where the hybrid layer
# relies on PHH. Uses the Parquet files, joined on the H3 index.
# =============================================================================
source("R/00_setup.R")

res <- 7
phh <- read_hex_parquet("phh", res) |> dplyr::select(h3, pop_phh = population)
nar <- read_hex_parquet("nar", res) |> dplyr::select(h3, pop_nar = population)

cmp <- dplyr::full_join(phh, nar, by = "h3") |>
  dplyr::mutate(dplyr::across(c(pop_phh, pop_nar), ~ dplyr::coalesce(.x, 0)),
                M = (pop_phh + pop_nar) / 2,
                diff = pop_nar - pop_phh,
                rel_diff = ifelse(M > 0, abs(diff) / M, NA_real_))

# Displaced population D and D/P (paper, Section 4.7)
P <- sum(cmp$pop_phh)
D <- 0.5 * sum(abs(cmp$diff))
cat(sprintf("Resolution %d: D = %s persons, D/P = %.1f%%\n",
            res, format(round(D), big.mark = ","), 100 * D / P))

# Agreement by cell size, for cells with mean population of 5 or more
cmp |>
  dplyr::filter(M >= 5) |>
  dplyr::mutate(category = cut(rel_diff, c(0, 0.05, 0.25, 0.5, Inf),
                               labels = c("Match", "Minor", "Moderate", "Major"),
                               right = FALSE)) |>
  dplyr::count(category) |>
  dplyr::mutate(share = n / sum(n))

# Scatter on log scales
p1 <- ggplot(dplyr::filter(cmp, M > 0), aes(pop_phh + 1, pop_nar + 1)) +
  geom_bin2d(bins = 80) +
  geom_abline(linetype = "dashed") +
  scale_x_log10(labels = scales::comma) +
  scale_y_log10(labels = scales::comma) +
  scale_fill_viridis_c(trans = "log10", name = "Cells") +
  labs(x = "PHH population + 1", y = "NAR population + 1",
       title = sprintf("PHH and NAR allocation by cell, resolution %d", res)) +
  theme_minimal()
ggsave(file.path(FIG_DIR, sprintf("phh_vs_nar_res%d.png", res)), p1,
       width = 6, height = 5, dpi = 300, bg = "white")

# Where does the hybrid layer use PHH? (Saskatchewan window)
sask_bbox <- c(-108.5, 50.5, -104.0, 53.0)
hyb_sk <- read_hex("hyb", res = res, bbox = sask_bbox) |>
  sf::st_transform(CRS_LAMBERT)
p2 <- ggplot(hyb_sk) +
  geom_sf(aes(fill = share_pop_from_phh_source), colour = NA) +
  scale_fill_viridis_c(option = "cividis", limits = c(0, 1),
                       name = "Share of population\nfrom PHH blocks") +
  labs(title = "Hybrid source, central Saskatchewan") +
  theme_void()
ggsave(file.path(FIG_DIR, sprintf("hyb_phh_share_sask_res%d.png", res)), p2,
       width = 7, height = 6, dpi = 300, bg = "white")
