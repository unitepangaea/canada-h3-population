# Validation of the v2 layers

This file reproduces, without modification, the output of `src/04_validate.py` for method version v2 (base hybrid and HYB-V), run on 2026-11-06. The checks are defined in `docs/METHODS.md`; the release-file checks written by `scripts/check_release.py` are in `docs/validation_v2_release.md`.

## Run log

```
# 2026-11-06 10:50:38
[     28s] V1-V3 v2 done
[     56s] V1-V3 v2_hybv done
[     64s] V4 v2 done
[     66s] V4 v2_hybv done
[     67s] V5 done
[    158s] DA polygons cached: 57,932
[    159s] V6: 56,686 populated DAs; 967 without active NAR locations
[    237s] V6 r=6 done
[    489s] V6 r=7 done
[   1811s] V6 r=8 done
[   1811s] V1 [PASS] DB-level conservation, method x r: max 8.0e-11 over 12 method x r layers
[   1811s] V2 [PASS] Province conservation (Eq. 8): max |eps(p)| 1.2e-10; national totals [36991971.0]
[   1811s] V3 [PASS] Cross-resolution invariance: max DB total diff 9.1e-13; s(d) identical
[   1811s] V4 [report] Non-nesting (parent aggregation vs direct): v2 hyb 8->7: D/P 2.424%, >1 person 48,920, max 3811.2; v2 hyb 8->6: D/P 2.185%, >1 person 18,936, max 9777.4; v2 hyb 7->6: D/P 2.234%, >1 person 20,360, max 13895.3; v2_hybv hyb 8->7: D/P 2.426%, >1 person 49,191, max 3775.2; v2_hybv hyb 8->6: D/P 2.186%, >1 person 18,987, max 9807.3; v2_hybv hyb 7->6: D/P 2.238%, >1 person 20,405, max 13883.8
[   1811s] V5 [PASS] NAR fallback diagnostics: r6: tier1 6,574, tier2 25,682, tier3 0, NAR-only cells 40,389, NAR cells <1 39,205; r7: tier1 19,657, tier2 12,599, tier3 0, NAR-only cells 316,628, NAR cells <1 301,741; r8: tier1 25,756, tier2 6,500, tier3 0, NAR-only cells 2,391,418, NAR cells <1 2,355,690
[   1811s] V6 [report] Hierarchical accuracy (DA -> cells vs DB-based NAR): r6 DA NAR-location weights (v2): MAE 10.31, RMSE 56.3, MdAPE(M>=5) 0.184, D/P 1.47%; r6 DA areal weighting (cell centres): MAE 29.56, RMSE 189.1, MdAPE(M>=5) 0.513, D/P 7.22%; r7 DA NAR-location weights (v2): MAE 3.00, RMSE 31.6, MdAPE(M>=5) 0.172, D/P 2.73%; r7 DA areal weighting (cell centres): MAE 8.52, RMSE 88.3, MdAPE(M>=5) 0.585, D/P 14.48%; r8 DA NAR-location weights (v2): MAE 0.81, RMSE 14.4, MdAPE(M>=5) 0.121, D/P 4.75%; r8 DA areal weighting (cell centres): MAE 2.27, RMSE 33.5, MdAPE(M>=5) 0.720, D/P 26.90%
```

## Summary

Source: `tables/validation_summary.csv`

| id | check | criterion | result | pass |
|---|---|---|---|---|
| V1 | DB-level conservation, method x r | max \|eps(d)\| < 1e-6 | max 8.0e-11 over 12 method x r layers | True |
| V2 | Province conservation (Eq. 8) | \|eps(p)\| < 1e-6; national 36,991,971 | max \|eps(p)\| 1.2e-10; national totals [36991971.0] | True |
| V3 | Cross-resolution invariance | exact (<= 1e-9) | max DB total diff 9.1e-13; s(d) identical | True |
| V4 | Non-nesting (parent aggregation vs direct) | report | v2 hyb 8->7: D/P 2.424%, >1 person 48,920, max 3811.2; v2 hyb 8->6: D/P 2.185%, >1 person 18,936, max 9777.4; v2 hyb 7->6: D/P 2.234%, >1 person 20,360, max 13895.3; v2_hybv hyb 8->7: D/P 2.426%, >1 person 49,191, max 3775.2; v2_hybv hyb 8->6: D/P 2.186%, >1 person 18,987, max 9807.3; v2_hybv hyb 7->6: D/P 2.238%, >1 person 20,405, max 13883.8 |  |
| V5 | NAR fallback diagnostics | report; tier-3 = 0 | r6: tier1 6,574, tier2 25,682, tier3 0, NAR-only cells 40,389, NAR cells <1 39,205; r7: tier1 19,657, tier2 12,599, tier3 0, NAR-only cells 316,628, NAR cells <1 301,741; r8: tier1 25,756, tier2 6,500, tier3 0, NAR-only cells 2,391,418, NAR cells <1 2,355,690 | True |
| V6 | Hierarchical accuracy (DA -> cells vs DB-based NAR) | report | r6 DA NAR-location weights (v2): MAE 10.31, RMSE 56.3, MdAPE(M>=5) 0.184, D/P 1.47%; r6 DA areal weighting (cell centres): MAE 29.56, RMSE 189.1, MdAPE(M>=5) 0.513, D/P 7.22%; r7 DA NAR-location weights (v2): MAE 3.00, RMSE 31.6, MdAPE(M>=5) 0.172, D/P 2.73%; r7 DA areal weighting (cell centres): MAE 8.52, RMSE 88.3, MdAPE(M>=5) 0.585, D/P 14.48%; r8 DA NAR-location weights (v2): MAE 0.81, RMSE 14.4, MdAPE(M>=5) 0.121, D/P 4.75%; r8 DA areal weighting (cell centres): MAE 2.27, RMSE 33.5, MdAPE(M>=5) 0.720, D/P 26.90% |  |

## V1. Block-level conservation

Source: `tables/validation_V1_db_conservation.csv`

| tag | method | res | n_dbs | max_abs_eps | n_dbs_over_tol | pass |
|---|---|---|---|---|---|---|
| v2 | phh | 6 | 498547 | 8.003553375601768e-11 | 0 | True |
| v2 | nar | 6 | 498547 | 4.547473508864641e-13 | 0 | True |
| v2 | hyb | 6 | 498547 | 8.003553375601768e-11 | 0 | True |
| v2 | phh | 7 | 498547 | 8.003553375601768e-11 | 0 | True |
| v2 | nar | 7 | 498547 | 4.547473508864641e-13 | 0 | True |
| v2 | hyb | 7 | 498547 | 8.003553375601768e-11 | 0 | True |
| v2 | phh | 8 | 498547 | 8.003553375601768e-11 | 0 | True |
| v2 | nar | 8 | 498547 | 4.547473508864641e-13 | 0 | True |
| v2 | hyb | 8 | 498547 | 8.003553375601768e-11 | 0 | True |
| v2_hybv | hyb | 6 | 498547 | 8.003553375601768e-11 | 0 | True |
| v2_hybv | hyb | 7 | 498547 | 8.003553375601768e-11 | 0 | True |
| v2_hybv | hyb | 8 | 498547 | 8.003553375601768e-11 | 0 | True |

## V2. Province and territory conservation

Source: `tables/validation_V2_province_conservation.csv`

| tag | method | res | PR | gaf_pop | layer_pop | eps | pass |
|---|---|---|---|---|---|---|---|
| v2 | phh | 6 | 10 | 510545.0 | 510544.99999999994 | -5.820766091346741e-11 | True |
| v2 | phh | 6 | 11 | 154331.0 | 154331.0 | 0.0 | True |
| v2 | phh | 6 | 12 | 969383.0 | 969383.0 | 0.0 | True |
| v2 | phh | 6 | 13 | 775610.0 | 775610.0 | 0.0 | True |
| v2 | phh | 6 | 24 | 8501833.0 | 8501833.0 | 0.0 | True |
| v2 | phh | 6 | 35 | 14223942.0 | 14223942.0 | 0.0 | True |
| v2 | phh | 6 | 46 | 1342153.0 | 1342153.0 | 0.0 | True |
| v2 | phh | 6 | 47 | 1132505.0 | 1132505.0 | 0.0 | True |
| v2 | phh | 6 | 48 | 4262635.0 | 4262635.0 | 0.0 | True |
| v2 | phh | 6 | 59 | 5000874.0 | 5000874.0 | 0.0 | True |
| v2 | phh | 6 | 60 | 40232.0 | 40232.000000000015 | 1.4551915228366852e-11 | True |
| v2 | phh | 6 | 61 | 41070.0 | 41069.999999999985 | -1.4551915228366852e-11 | True |
| v2 | phh | 6 | 62 | 36858.0 | 36857.99999999999 | -7.275957614183426e-12 | True |
| v2 | phh | 6 | Canada | 36991971.0 | 36991971.0 | 0.0 | True |
| v2 | nar | 6 | 10 | 510545.0 | 510545.0 | 0.0 | True |
| v2 | nar | 6 | 11 | 154331.0 | 154331.0 | 0.0 | True |
| v2 | nar | 6 | 12 | 969383.0 | 969383.0 | 0.0 | True |
| v2 | nar | 6 | 13 | 775610.0 | 775610.0 | 0.0 | True |
| v2 | nar | 6 | 24 | 8501833.0 | 8501833.0 | 0.0 | True |
| v2 | nar | 6 | 35 | 14223942.0 | 14223942.0 | 0.0 | True |
| v2 | nar | 6 | 46 | 1342153.0 | 1342153.0 | 0.0 | True |
| v2 | nar | 6 | 47 | 1132505.0 | 1132505.0 | 0.0 | True |
| v2 | nar | 6 | 48 | 4262635.0 | 4262635.0 | 0.0 | True |
| v2 | nar | 6 | 59 | 5000874.0 | 5000874.0 | 0.0 | True |
| v2 | nar | 6 | 60 | 40232.0 | 40232.0 | 0.0 | True |
| v2 | nar | 6 | 61 | 41070.0 | 41070.0 | 0.0 | True |
| v2 | nar | 6 | 62 | 36858.0 | 36858.0 | 0.0 | True |
| v2 | nar | 6 | Canada | 36991971.0 | 36991971.0 | 0.0 | True |
| v2 | hyb | 6 | 10 | 510545.0 | 510545.0 | 0.0 | True |
| v2 | hyb | 6 | 11 | 154331.0 | 154331.0 | 0.0 | True |
| v2 | hyb | 6 | 12 | 969383.0 | 969383.0 | 0.0 | True |
| v2 | hyb | 6 | 13 | 775610.0 | 775610.0 | 0.0 | True |
| v2 | hyb | 6 | 24 | 8501833.0 | 8501833.0 | 0.0 | True |
| v2 | hyb | 6 | 35 | 14223942.0 | 14223942.0 | 0.0 | True |
| v2 | hyb | 6 | 46 | 1342153.0 | 1342153.0 | 0.0 | True |
| v2 | hyb | 6 | 47 | 1132505.0 | 1132505.0 | 0.0 | True |
| v2 | hyb | 6 | 48 | 4262635.0 | 4262635.0 | 0.0 | True |
| v2 | hyb | 6 | 59 | 5000874.0 | 5000874.0 | 0.0 | True |
| v2 | hyb | 6 | 60 | 40232.0 | 40232.0 | 0.0 | True |
| v2 | hyb | 6 | 61 | 41070.0 | 41070.0 | 0.0 | True |
| v2 | hyb | 6 | 62 | 36858.0 | 36858.0 | 0.0 | True |
| v2 | hyb | 6 | Canada | 36991971.0 | 36991971.0 | 0.0 | True |
| v2 | phh | 7 | 10 | 510545.0 | 510544.99999999994 | -5.820766091346741e-11 | True |
| v2 | phh | 7 | 11 | 154331.0 | 154331.0 | 0.0 | True |
| v2 | phh | 7 | 12 | 969383.0 | 969383.0 | 0.0 | True |
| v2 | phh | 7 | 13 | 775610.0 | 775610.0 | 0.0 | True |
| v2 | phh | 7 | 24 | 8501833.0 | 8501833.0 | 0.0 | True |
| v2 | phh | 7 | 35 | 14223942.0 | 14223942.0 | 0.0 | True |
| v2 | phh | 7 | 46 | 1342153.0 | 1342153.0 | 0.0 | True |
| v2 | phh | 7 | 47 | 1132505.0 | 1132505.0 | 0.0 | True |
| v2 | phh | 7 | 48 | 4262635.0 | 4262635.0 | 0.0 | True |
| v2 | phh | 7 | 59 | 5000874.0 | 5000874.0 | 0.0 | True |
| v2 | phh | 7 | 60 | 40232.0 | 40232.000000000015 | 1.4551915228366852e-11 | True |
| v2 | phh | 7 | 61 | 41070.0 | 41069.999999999985 | -1.4551915228366852e-11 | True |
| v2 | phh | 7 | 62 | 36858.0 | 36857.99999999999 | -7.275957614183426e-12 | True |
| v2 | phh | 7 | Canada | 36991971.0 | 36991971.0 | 0.0 | True |
| v2 | nar | 7 | 10 | 510545.0 | 510545.0 | 0.0 | True |
| v2 | nar | 7 | 11 | 154331.0 | 154331.0 | 0.0 | True |
| v2 | nar | 7 | 12 | 969383.0 | 969383.0 | 0.0 | True |
| v2 | nar | 7 | 13 | 775610.0 | 775610.0 | 0.0 | True |
| v2 | nar | 7 | 24 | 8501833.0 | 8501833.0 | 0.0 | True |
| v2 | nar | 7 | 35 | 14223942.0 | 14223942.0 | 0.0 | True |
| v2 | nar | 7 | 46 | 1342153.0 | 1342153.0 | 0.0 | True |
| v2 | nar | 7 | 47 | 1132505.0 | 1132505.0 | 0.0 | True |
| v2 | nar | 7 | 48 | 4262635.0 | 4262635.0 | 0.0 | True |
| v2 | nar | 7 | 59 | 5000874.0 | 5000874.0 | 0.0 | True |
| v2 | nar | 7 | 60 | 40232.0 | 40232.0 | 0.0 | True |
| v2 | nar | 7 | 61 | 41070.0 | 41070.0 | 0.0 | True |
| v2 | nar | 7 | 62 | 36858.0 | 36858.0 | 0.0 | True |
| v2 | nar | 7 | Canada | 36991971.0 | 36991971.0 | 0.0 | True |
| v2 | hyb | 7 | 10 | 510545.0 | 510545.0 | 0.0 | True |
| v2 | hyb | 7 | 11 | 154331.0 | 154331.0 | 0.0 | True |
| v2 | hyb | 7 | 12 | 969383.0 | 969383.0 | 0.0 | True |
| v2 | hyb | 7 | 13 | 775610.0 | 775610.0 | 0.0 | True |
| v2 | hyb | 7 | 24 | 8501833.0 | 8501833.0 | 0.0 | True |
| v2 | hyb | 7 | 35 | 14223942.0 | 14223942.0 | 0.0 | True |
| v2 | hyb | 7 | 46 | 1342153.0 | 1342153.0 | 0.0 | True |
| v2 | hyb | 7 | 47 | 1132505.0 | 1132505.0 | 0.0 | True |
| v2 | hyb | 7 | 48 | 4262635.0 | 4262635.0 | 0.0 | True |
| v2 | hyb | 7 | 59 | 5000874.0 | 5000874.0 | 0.0 | True |
| v2 | hyb | 7 | 60 | 40232.0 | 40232.0 | 0.0 | True |
| v2 | hyb | 7 | 61 | 41070.0 | 41070.0 | 0.0 | True |
| v2 | hyb | 7 | 62 | 36858.0 | 36858.0 | 0.0 | True |
| v2 | hyb | 7 | Canada | 36991971.0 | 36991971.0 | 0.0 | True |
| v2 | phh | 8 | 10 | 510545.0 | 510544.9999999999 | -1.1641532182693481e-10 | True |
| v2 | phh | 8 | 11 | 154331.0 | 154331.0 | 0.0 | True |
| v2 | phh | 8 | 12 | 969383.0 | 969383.0 | 0.0 | True |
| v2 | phh | 8 | 13 | 775610.0 | 775610.0 | 0.0 | True |
| v2 | phh | 8 | 24 | 8501833.0 | 8501833.0 | 0.0 | True |
| v2 | phh | 8 | 35 | 14223942.0 | 14223942.0 | 0.0 | True |
| v2 | phh | 8 | 46 | 1342153.0 | 1342153.0 | 0.0 | True |
| v2 | phh | 8 | 47 | 1132505.0 | 1132505.0 | 0.0 | True |
| v2 | phh | 8 | 48 | 4262635.0 | 4262635.0 | 0.0 | True |
| v2 | phh | 8 | 59 | 5000874.0 | 5000874.0 | 0.0 | True |
| v2 | phh | 8 | 60 | 40232.0 | 40232.000000000015 | 1.4551915228366852e-11 | True |
| v2 | phh | 8 | 61 | 41070.0 | 41069.999999999985 | -1.4551915228366852e-11 | True |
| v2 | phh | 8 | 62 | 36858.0 | 36858.0 | 0.0 | True |
| v2 | phh | 8 | Canada | 36991971.0 | 36991971.0 | 0.0 | True |
| v2 | nar | 8 | 10 | 510545.0 | 510545.0 | 0.0 | True |
| v2 | nar | 8 | 11 | 154331.0 | 154331.0 | 0.0 | True |
| v2 | nar | 8 | 12 | 969383.0 | 969383.0 | 0.0 | True |
| v2 | nar | 8 | 13 | 775610.0 | 775610.0 | 0.0 | True |
| v2 | nar | 8 | 24 | 8501833.0 | 8501833.0 | 0.0 | True |
| v2 | nar | 8 | 35 | 14223942.0 | 14223942.0 | 0.0 | True |
| v2 | nar | 8 | 46 | 1342153.0 | 1342153.0 | 0.0 | True |
| v2 | nar | 8 | 47 | 1132505.0 | 1132505.0 | 0.0 | True |
| v2 | nar | 8 | 48 | 4262635.0 | 4262635.0 | 0.0 | True |
| v2 | nar | 8 | 59 | 5000874.0 | 5000874.0 | 0.0 | True |
| v2 | nar | 8 | 60 | 40232.0 | 40232.0 | 0.0 | True |
| v2 | nar | 8 | 61 | 41070.0 | 41070.0 | 0.0 | True |
| v2 | nar | 8 | 62 | 36858.0 | 36858.0 | 0.0 | True |
| v2 | nar | 8 | Canada | 36991971.0 | 36991971.0 | 0.0 | True |
| v2 | hyb | 8 | 10 | 510545.0 | 510545.0 | 0.0 | True |
| v2 | hyb | 8 | 11 | 154331.0 | 154331.0 | 0.0 | True |
| v2 | hyb | 8 | 12 | 969383.0 | 969383.0 | 0.0 | True |
| v2 | hyb | 8 | 13 | 775610.0 | 775610.0 | 0.0 | True |
| v2 | hyb | 8 | 24 | 8501833.0 | 8501833.0 | 0.0 | True |
| v2 | hyb | 8 | 35 | 14223942.0 | 14223942.0 | 0.0 | True |
| v2 | hyb | 8 | 46 | 1342153.0 | 1342153.0 | 0.0 | True |
| v2 | hyb | 8 | 47 | 1132505.0 | 1132505.0 | 0.0 | True |
| v2 | hyb | 8 | 48 | 4262635.0 | 4262635.0 | 0.0 | True |
| v2 | hyb | 8 | 59 | 5000874.0 | 5000874.0 | 0.0 | True |
| v2 | hyb | 8 | 60 | 40232.0 | 40232.0 | 0.0 | True |
| v2 | hyb | 8 | 61 | 41070.0 | 41070.0 | 0.0 | True |
| v2 | hyb | 8 | 62 | 36858.0 | 36858.0 | 0.0 | True |
| v2 | hyb | 8 | Canada | 36991971.0 | 36991971.0 | 0.0 | True |
| v2_hybv | hyb | 6 | 10 | 510545.0 | 510545.0 | 0.0 | True |
| v2_hybv | hyb | 6 | 11 | 154331.0 | 154331.0 | 0.0 | True |
| v2_hybv | hyb | 6 | 12 | 969383.0 | 969383.0 | 0.0 | True |
| v2_hybv | hyb | 6 | 13 | 775610.0 | 775610.0 | 0.0 | True |
| v2_hybv | hyb | 6 | 24 | 8501833.0 | 8501833.0 | 0.0 | True |
| v2_hybv | hyb | 6 | 35 | 14223942.0 | 14223942.0 | 0.0 | True |
| v2_hybv | hyb | 6 | 46 | 1342153.0 | 1342153.0 | 0.0 | True |
| v2_hybv | hyb | 6 | 47 | 1132505.0 | 1132505.0 | 0.0 | True |
| v2_hybv | hyb | 6 | 48 | 4262635.0 | 4262635.0 | 0.0 | True |
| v2_hybv | hyb | 6 | 59 | 5000874.0 | 5000874.0 | 0.0 | True |
| v2_hybv | hyb | 6 | 60 | 40232.0 | 40232.0 | 0.0 | True |
| v2_hybv | hyb | 6 | 61 | 41070.0 | 41070.0 | 0.0 | True |
| v2_hybv | hyb | 6 | 62 | 36858.0 | 36857.99999999999 | -7.275957614183426e-12 | True |
| v2_hybv | hyb | 6 | Canada | 36991971.0 | 36991971.0 | 0.0 | True |
| v2_hybv | hyb | 7 | 10 | 510545.0 | 510545.0 | 0.0 | True |
| v2_hybv | hyb | 7 | 11 | 154331.0 | 154331.0 | 0.0 | True |
| v2_hybv | hyb | 7 | 12 | 969383.0 | 969383.0 | 0.0 | True |
| v2_hybv | hyb | 7 | 13 | 775610.0 | 775610.0 | 0.0 | True |
| v2_hybv | hyb | 7 | 24 | 8501833.0 | 8501833.0 | 0.0 | True |
| v2_hybv | hyb | 7 | 35 | 14223942.0 | 14223942.0 | 0.0 | True |
| v2_hybv | hyb | 7 | 46 | 1342153.0 | 1342153.0 | 0.0 | True |
| v2_hybv | hyb | 7 | 47 | 1132505.0 | 1132505.0 | 0.0 | True |
| v2_hybv | hyb | 7 | 48 | 4262635.0 | 4262635.0 | 0.0 | True |
| v2_hybv | hyb | 7 | 59 | 5000874.0 | 5000874.0 | 0.0 | True |
| v2_hybv | hyb | 7 | 60 | 40232.0 | 40232.0 | 0.0 | True |
| v2_hybv | hyb | 7 | 61 | 41070.0 | 41070.0 | 0.0 | True |
| v2_hybv | hyb | 7 | 62 | 36858.0 | 36857.99999999999 | -7.275957614183426e-12 | True |
| v2_hybv | hyb | 7 | Canada | 36991971.0 | 36991971.0 | 0.0 | True |
| v2_hybv | hyb | 8 | 10 | 510545.0 | 510545.0 | 0.0 | True |
| v2_hybv | hyb | 8 | 11 | 154331.0 | 154331.0 | 0.0 | True |
| v2_hybv | hyb | 8 | 12 | 969383.0 | 969383.0 | 0.0 | True |
| v2_hybv | hyb | 8 | 13 | 775610.0 | 775610.0 | 0.0 | True |
| v2_hybv | hyb | 8 | 24 | 8501833.0 | 8501833.0 | 0.0 | True |
| v2_hybv | hyb | 8 | 35 | 14223942.0 | 14223942.0 | 0.0 | True |
| v2_hybv | hyb | 8 | 46 | 1342153.0 | 1342153.0 | 0.0 | True |
| v2_hybv | hyb | 8 | 47 | 1132505.0 | 1132505.0 | 0.0 | True |
| v2_hybv | hyb | 8 | 48 | 4262635.0 | 4262635.0 | 0.0 | True |
| v2_hybv | hyb | 8 | 59 | 5000874.0 | 5000874.0 | 0.0 | True |
| v2_hybv | hyb | 8 | 60 | 40232.0 | 40232.0 | 0.0 | True |
| v2_hybv | hyb | 8 | 61 | 41070.0 | 41070.0 | 0.0 | True |
| v2_hybv | hyb | 8 | 62 | 36858.0 | 36857.99999999999 | -7.275957614183426e-12 | True |
| v2_hybv | hyb | 8 | Canada | 36991971.0 | 36991971.0 | 0.0 | True |

## V3. Cross-resolution invariance of block totals

Source: `tables/validation_V3_invariance.csv`

| tag | check | max_abs_diff_across_r | pass | note |
|---|---|---|---|---|
| v2 | DB total contribution, phh | 9.094947017729282e-13 | True |  |
| v2 | DB total contribution, nar | 5.684341886080801e-13 | True |  |
| v2 | DB total contribution, hyb | 4.547473508864641e-13 | True |  |
| v2 | hybrid source s(d) per DB | 0.0 | True | identical across r: True; DBs with mixed sources: 0; equals db_table s_final: True |
| v2_hybv | DB total contribution, hyb | 4.547473508864641e-13 | True |  |
| v2_hybv | hybrid source s(d) per DB | 0.0 | True | identical across r: True; DBs with mixed sources: 0; equals db_table s_final: True |

## V4. Non-nesting: parent aggregation compared with direct binning (report only)

Source: `tables/validation_V4_nesting.csv`

| tag | method | from_res | to_res | cells_direct | cells_aggregated | cells_union | D | D_over_P_pct | n_cells_diff_gt1 | pct_cells_diff_gt1 | max_abs_diff | cell_max_abs_diff |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v2 | phh | 8 | 7 | 145520 | 146261 | 149269 | 776186.4738707434 | 2.098256602414463 | 68673 | 46.006203565375266 | 3852.7397042437224 | 872b9bc55ffffff |
| v2 | nar | 8 | 7 | 434403 | 461167 | 462907 | 966872.0831911261 | 2.613734972897568 | 68479 | 14.793252208326942 | 3045.369103367444 | 872baa450ffffff |
| v2 | hyb | 8 | 7 | 129935 | 130295 | 133613 | 896821.4396696757 | 2.424367816653175 | 48920 | 36.613203805018976 | 3811.173032883955 | 872b9bc76ffffff |
| v2 | phh | 8 | 6 | 36661 | 36929 | 37256 | 774870.1417225273 | 2.0946981757812457 | 21442 | 57.55314580201847 | 9931.30540573073 | 862baa44fffffff |
| v2 | nar | 8 | 6 | 72577 | 79279 | 79444 | 853818.3269150106 | 2.3081179613679157 | 24930 | 31.380595136196565 | 9654.681114865962 | 862b9bc47ffffff |
| v2 | hyb | 8 | 6 | 33891 | 34099 | 34432 | 808113.4281143398 | 2.184564396729063 | 18936 | 54.9953531598513 | 9777.40056751194 | 862b9bc47ffffff |
| v2 | phh | 7 | 6 | 36661 | 36881 | 37292 | 795092.2864936114 | 2.1493644836973176 | 22877 | 61.345596910865595 | 13333.248532898608 | 862b9bc47ffffff |
| v2 | nar | 7 | 6 | 72577 | 77370 | 77617 | 868063.6706553708 | 2.346627246910879 | 24317 | 31.32947678987851 | 12801.782607944944 | 862b9bc47ffffff |
| v2 | hyb | 7 | 6 | 33891 | 34086 | 34491 | 826368.1759073366 | 2.233912261412988 | 20360 | 59.02989185584645 | 13895.324212785112 | 862b9bc47ffffff |
| v2_hybv | hyb | 8 | 7 | 130306 | 130667 | 133983 | 897246.4529112593 | 2.4255167504085122 | 49191 | 36.71435928438683 | 3775.183902449171 | 872b9bc76ffffff |
| v2_hybv | hyb | 8 | 6 | 34012 | 34223 | 34562 | 808631.6565709058 | 2.185965318179196 | 18987 | 54.93605694114924 | 9807.343263234303 | 862b9bc47ffffff |
| v2_hybv | hyb | 7 | 6 | 34012 | 34212 | 34622 | 827906.4484601334 | 2.2380706571708044 | 20405 | 58.936514355034376 | 13883.799434931396 | 862b9bc47ffffff |

## V5. NAR areal-fallback diagnostics

Source: `tables/validation_V5_fallback.csv`

| res | tier1_dbs | tier1_pop | tier2_dbs | tier2_pop | tier3_dbs | tier3_pop | nar_only_cells | nar_only_pop | phh_cells | phh_cells_lt1 | phh_pct_cells_lt1 | nar_cells | nar_cells_lt1 | nar_pct_cells_lt1 | hyb_cells | hyb_cells_lt1 | hyb_pct_cells_lt1 | pass_tier3_zero |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 6 | 6574 | 147544.0 | 25682 | 412185.0 | 0 | 0.0 | 40389 | 32515.81433925183 | 36661 | 2500 | 6.819235700062737 | 72577 | 39205 | 54.01849070642214 | 33891 | 1750 | 5.163612758549467 | True |
| 7 | 19657 | 328154.0 | 12599 | 231575.0 | 0 | 0.0 | 316628 | 134709.27948591346 | 145520 | 10181 | 6.996289169873557 | 434403 | 301741 | 69.46107646586235 | 129935 | 6994 | 5.3826913456728365 | True |
| 8 | 25756 | 419963.0 | 6500 | 139766.0 | 0 | 0.0 | 2391418 | 467010.2460257245 | 410283 | 32143 | 7.834348486288732 | 2656940 | 2355690 | 88.66176880170421 | 307060 | 20029 | 6.522829414446688 | True |

## V6. Hierarchical accuracy test (report only)

Source: `tables/validation_V6_hierarchical.csv`

| res | estimator | total | unallocated_DAs | cells_union | MAE | RMSE | median_APE_M5 | n_cells_M5 | D_over_P_pct |
|---|---|---|---|---|---|---|---|---|---|
| 6 | DA NAR-location weights (v2) | 36991971.00000001 | 0 | 105497 | 10.306561573188635 | 56.33775570723158 | 0.18381747106596397 | 29647 | 1.4696585460216238 |
| 6 | DA areal weighting (cell centres) | 36991971.0 | 0 | 180645 | 29.556633869422487 | 189.07734077794714 | 0.5128057427400179 | 29647 | 7.216779724094486 |
| 7 | DA NAR-location weights (v2) | 36991971.0 | 0 | 674839 | 2.9962096759199617 | 31.569830322336873 | 0.1719584104033684 | 97394 | 2.7329702727764236 |
| 7 | DA areal weighting (cell centres) | 36991971.0 | 0 | 1257309 | 8.518708896095069 | 88.34999090121785 | 0.5850241518881528 | 97394 | 14.476991998399322 |
| 8 | DA NAR-location weights (v2) | 36991971.0 | 0 | 4341301 | 0.808960082210234 | 14.374001375404458 | 0.12149991812673983 | 192569 | 4.746893878484294 |
| 8 | DA areal weighting (cell centres) | 36991970.99999999 | 0 | 8783998 | 2.2658330763099475 | 33.50358827770107 | 0.7202449034515239 | 192569 | 26.901882587765364 |
