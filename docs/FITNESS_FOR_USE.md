# Fitness for use

The layers are modelled estimates of where residents live within each 2021 Dissemination Block. This document sets out what each resolution is suited to, the known limitations, and the checks that users should make before analysis. The evidence for each point is reported in the paper and in `docs/validation_v2.md`.

## 1. Choosing a resolution

Producing the surface at three resolutions from one point-level allocation gives a family of layers that are consistent by construction, since every resolution conserves the same block totals and assigns each block to the same source.

| Resolution | Mean cell area | Suited to | Use with caution for |
|---|---|---|---|
| 6 | 36.1 km² | National and provincial maps; regional comparison; rural and northern analysis where blocks are themselves large; stable rate denominators | Urban fringes, coastlines and lakeshores, where density is averaged across settled and unsettled land |
| 7 | 5.2 km² | Community, small-town and rural service-area analysis; travel-time catchments in rural areas; linkage to environmental surfaces of about 1 to 2 km | Dense urban cores, where variation within cells is large |
| 8 | 0.74 km² | Neighbourhood analysis in cities; linkage to environmental surfaces of about 1 km or finer; travel-time catchments in urban areas | Rates and small counts in rural and northern areas; any use where very small counts are a disclosure concern |

Repeating an analysis at resolutions 6, 7 and 8 is a direct test of sensitivity to the modifiable areal unit problem.

## 2. Known limitations

1. **Allocation within blocks.** Cell values below the block level are allocations, not counts. Agreement between the independent PHH and NAR methods is reported in the paper and indicates where the placement of population is uncertain.
2. **Non-nesting of H3 cells.** H3 children do not fit exactly inside their parents. Aggregating the resolution 8 layer with `cell_to_parent` gives values that differ slightly from the directly built resolution 7 and 6 layers. Use the layer released for each resolution. The size of the difference is reported in the validation file (check V4).
3. **Scale and apparent agreement.** Coarser cells force agreement between methods wherever a block lies entirely inside one cell. Lower disagreement at coarser resolutions therefore reflects both better placement and this mechanical effect. The forced-agreement share at each resolution is reported in the paper.
4. **Temporal mismatch.** The population is from the 2021 Census and the address register is from June 2026. In blocks with substantial post-2021 construction, the NAR and hybrid layers may place 2021 residents at addresses that did not exist in 2021. The `vintage_flag` in the block table identifies these blocks, and the `hybv` layer provides a sensitivity alternative.
5. **Equal weighting of NAR locations.** Each residential NAR location receives an equal share of block population, regardless of the number of units in the building. In blocks with mixed high-rise and low-rise housing, population may be under-allocated to high-rise buildings.
6. **Thin address coverage.** Address coverage is lower in parts of Saskatchewan and the territories. The hybrid rule allocates these blocks from PHH, and the `share_pop_from_phh_source` column shows where this occurs.
7. **Small counts.** Many populated cells at resolution 8 contain fewer than five persons, especially in rural and northern areas. Coarser resolutions reduce this. Small counts are an outcome of the model and are not themselves confidential, but they should not be reported as observed counts of residents.

## 3. Recommended checks before analysis

1. Confirm that the totals of your study area match published block or census subdivision totals.
2. Map `share_pop_from_phh_source` (hybrid) for your study area to see which source dominates.
3. Check `low_count_flag` before computing rates, and move to a coarser resolution if many cells are flagged.
4. For growth areas, compare results using `hyb` and `hybv`.
5. Report the layer name, version and resolution used, and cite the Zenodo DOI for that version.
