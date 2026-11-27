# Changelog

Versions follow the method version used in the paper. Each release has its own Zenodo DOI; the concept DOI always resolves to the latest release.

## [2.0.0] – 2026-11-27
Archived on Zenodo as doi:10.5281/zenodo.24592693 (concept DOI doi:10.5281/zenodo.24592692). The GitHub release for this version is tagged `v1.0.0`.

- Layers at H3 resolutions 6, 7 and 8, each binned directly from points (not aggregated from resolution 8).
- M1: NAR locations restricted to residential and partial-residential building use (BU_USE 1, 2).
- M2: NAR point-in-polygon assignment uses the 2021 DB digital boundary file.
- M3: Vintage check flags DBs with probable post-2021 growth; sensitivity layer HYB-V.
- H3 edge lengths reported from H3 v4.
- Block-level allocation tables released alongside the hexagon layers.

## [1.0.0] – layers as described in the preprint (v1)
- Resolution 8 only; NAR locations unfiltered; cartographic DB boundaries.
- Matches doi:10.20944/preprints202609.2636.v1.
