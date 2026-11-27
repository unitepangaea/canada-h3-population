# Methods summary

This summary is intended to help users understand the layers. The full method, equations and evaluation are given in the paper (McGaughey and Peters, 2026, doi:10.20944/preprints202609.2636.v1) and its revision.

## 1. Population base

The population input is the 2021 Census Dissemination Block (DB) population from the Statistics Canada Geographic Attribute File (`DBPOP2021_IDPOP2021`), covering 384,284 populated blocks and a national total of 36,991,971 persons. Every layer conserves these block totals exactly, so the layers differ only in how each block's population is placed within the block.

## 2. Allocation methods

**Pseudo-Household (PHH).** Innovation, Science and Economic Development Canada distributes 2021 block population to points along road segments. The population of each point is summed into the H3 cell that contains it.

**National Address Register (NAR).** Each block's population is divided equally among its residential NAR locations, using the building-footprint representative point of each location. In version 2, locations are retained when at least one of their addresses has a building use code of residential or partial residential (`BU_USE` 1 or 2), and locations are assigned to blocks with the 2021 digital boundary file. Blocks with no NAR location receive an areal fallback on the cartographic block polygon, which excludes water.

**Hybrid (HYB).** The hybrid rule assigns each block to one source. A block is allocated from NAR unless it has no NAR location, or its population per NAR location exceeds τ = 50, in which case it is allocated from PHH. The threshold τ identifies blocks where address coverage is too thin to represent the distribution of residents. Because the rule depends only on block-level quantities, a block's source is the same at every resolution.

## 3. Resolutions

Points are assigned directly to cells at resolutions 6, 7 and 8 with the H3 `latlng_to_cell` function. The coarser layers are not built by aggregating resolution 8 cells to their parents, because H3 child cells do not nest exactly within their parent cells.

## 4. Vintage check (version 2)

The population is from 2021 and the address register is from 2026. For each block, the ratio of residential address records to PHH 2021 dwellings is computed, and blocks with a ratio above 1.5 and at least 10 more addresses than 2021 dwellings are flagged as probable post-2021 growth. The `hybv` sensitivity layer allocates these blocks from PHH.

## 5. Validation

Each release is checked for exact conservation at the block, province and national levels, for identical source assignment across resolutions, and for reproduction of the published preprint values (version 1, resolution 8). Results are reported in `docs/validation_v2.md`.

## 6. Software

The pipeline is written in Python with h3 (version 4 or later), GeoPandas, Shapely, pyogrio and pyarrow. Exact versions are pinned in `src/requirements.txt`, and the H3, GEOS and PROJ versions used for each release are recorded in `src/ENVIRONMENT.md`.
