# =============================================================================
# 00_setup.R
# Packages, paths and helper functions used by the other example scripts.
# Run from the repository root:  source("R/00_setup.R")
# =============================================================================

# ---- Packages ---------------------------------------------------------------
pkgs <- c("sf", "dplyr", "ggplot2", "arrow", "h3jsr", "scales")
missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing) > 0) install.packages(missing)
invisible(lapply(pkgs, library, character.only = TRUE))

sf::sf_use_s2(FALSE)  # planar operations on small windows are adequate here

# ---- Paths and release settings ---------------------------------------------
DATA_DIR       <- "data"
FIG_DIR        <- "figures"
VERSION        <- "v2"
ZENODO_RECORD  <- "XXXXXXX"   # TODO: Zenodo record number after release
dir.create(FIG_DIR, showWarnings = FALSE)

# Coordinate reference systems
CRS_LAMBERT <- 3347           # Statistics Canada Lambert, for national maps
CRS_ALBERS  <- "ESRI:102001"  # Canada Albers Equal Area, for areas

# Density classes shared by every map, so resolutions can be compared directly
DENSITY_BREAKS <- c(0, 1, 10, 100, 1000, 5000, Inf)
DENSITY_LABELS <- c("< 1", "1\u201310", "10\u2013100", "100\u20131,000", "1,000\u20135,000", "5,000+")

# ---- File names ---------------------------------------------------------------
hex_file <- function(layer = "hyb", res = 8, format = "gpkg", version = VERSION) {
  file.path(DATA_DIR, sprintf("hexpop_%s_%s_res%d.%s", layer, version, res, format))
}

# ---- Read a hexagon layer -----------------------------------------------------
# layer : "hyb", "phh", "nar" or "hybv"
# res   : 6, 7 or 8
# bbox  : optional c(xmin, ymin, xmax, ymax) in longitude/latitude. Only cells
#         intersecting the box are read, which keeps memory use low for
#         resolution 8 (about 2.7 million cells nationally).
read_hex <- function(layer = "hyb", res = 8, bbox = NULL, version = VERSION) {
  f <- hex_file(layer, res, "gpkg", version)
  if (!file.exists(f)) stop("File not found: ", f, ". See data/README.md.")
  if (is.null(bbox)) return(sf::st_read(f, quiet = TRUE))
  box <- sf::st_as_sfc(sf::st_bbox(c(xmin = bbox[1], ymin = bbox[2],
                                     xmax = bbox[3], ymax = bbox[4]),
                                   crs = 4326))
  sf::st_read(f, wkt_filter = sf::st_as_text(box), quiet = TRUE)
}

# Read the Parquet version (no geometry) and, optionally, build hexagons.
read_hex_parquet <- function(layer = "hyb", res = 8, polygons = FALSE,
                             version = VERSION) {
  f <- hex_file(layer, res, "parquet", version)
  if (!file.exists(f)) stop("File not found: ", f, ". See data/README.md.")
  df <- arrow::read_parquet(f)
  if (!polygons) return(df)
  geom <- h3jsr::cell_to_polygon(df$h3, simple = TRUE)
  sf::st_sf(df, geometry = geom)
}

# Add the shared density classes to a layer
add_density_class <- function(x) {
  x$density_class <- cut(x$pop_density_km2, breaks = DENSITY_BREAKS,
                         labels = DENSITY_LABELS, right = FALSE)
  x
}

# ---- Download and verify ------------------------------------------------------
download_layer <- function(file_name, dest = DATA_DIR) {
  url <- sprintf("https://zenodo.org/records/%s/files/%s?download=1",
                 ZENODO_RECORD, file_name)
  out <- file.path(dest, file_name)
  options(timeout = max(3600, getOption("timeout")))
  utils::download.file(url, out, mode = "wb")
  check_manifest(dest, files = file_name)
  invisible(out)
}

check_manifest <- function(dir = DATA_DIR, files = NULL) {
  man <- utils::read.csv(file.path(dir, "MANIFEST.csv"), stringsAsFactors = FALSE)
  if (!is.null(files)) man <- man[man$file %in% files, ]
  man <- man[file.exists(file.path(dir, man$file)), ]
  if (nrow(man) == 0) {
    message("No downloaded files listed in MANIFEST.csv were found in ", dir)
    return(invisible(NULL))
  }
  if (!requireNamespace("digest", quietly = TRUE)) install.packages("digest")
  man$sha256_local <- vapply(file.path(dir, man$file), digest::digest,
                             character(1), algo = "sha256", file = TRUE)
  man$ok <- man$sha256_local == man$sha256
  print(man[, c("file", "ok")], row.names = FALSE)
  if (!all(man$ok)) warning("Checksum mismatch: re-download the files marked FALSE.")
  invisible(man)
}
