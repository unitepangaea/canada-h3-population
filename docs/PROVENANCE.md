# Data provenance

All inputs are open data published by the Government of Canada. The table records the exact release of each input used to build the layers, so that the layers can be reproduced and so that differences between releases can be traced.

| Input | Publisher | Release / vintage | Source | Retrieved | SHA-256 |
|---|---|---|---|---|---|
| Dissemination Block digital boundary file (`ldb_000a21a_e`) | Statistics Canada | 2021 Census | https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index2021-eng.cfm | 2026-11-06 | `42ee692c6c919bc7c97477f6e15e1d9e3215887c55dd8e7548733f3d3476fc7e` (`ldb_000a21a_e.zip`) |
| Dissemination Block cartographic boundary file (`ldb_000b21a_e`) | Statistics Canada | 2021 Census | As above | Not recorded | `b6f9294237a300f6c9bfb7f9001039916150bfb0ec9b2980fb2caa043382756f` (`ldb_000b21a_e.shp`)<sup>a</sup> |
| Geographic Attribute File | Statistics Canada | 2021 Census | https://www150.statcan.gc.ca/n1/en/catalogue/92-151-X | Not recorded | `3c089d2a1832cbef498afde36af186236f8bd98e9839dd681995303f7ea7ba99` (`GAF2021.csv`)<sup>a</sup> |
| National Address Register, Locations and Addresses (`NAR-202606`) | Statistics Canada | June 2026 extract | https://www150.statcan.gc.ca/n1/en/catalogue/46-26-0002 | Not recorded | Not recorded |
| Pseudo-Household Demographic Distribution | Innovation, Science and Economic Development Canada | 2021 | https://open.canada.ca/data/en/dataset/b3a1d603-19ca-466c-ae95-b5185e56addf | 2026-11-06 | `6bf9b215bf16d6cc9875d0a8d09856088461af9d1d0c79f3766d553f2f00d1c2` (`PHH_2021_CSV.zip`) |

<sup>a</sup> Computed on 2026-11-27 from the local copy used to build the v2 layers; the download date and the archive checksum were not recorded at the time of retrieval.

Retrieval dates and checksums for the digital boundary file and the Pseudo-Household files are taken from `docs/input_MANIFEST.csv` (a copy of `data_raw/MANIFEST.csv`), which also lists a checksum for each extracted Pseudo-Household CSV file.

## Expected input checks

These values are used by the pipeline to confirm that the correct release has been downloaded.

| Check | Expected value |
|---|---|
| PHH point rows | 16,614,053 |
| Populated Dissemination Blocks | 384,284 |
| National population | 36,991,971 |
| PHH population summed by block | Equals Geographic Attribute File block population within 1e-6 |

## Attribution

- Adapted from Statistics Canada, 2021 Census of Population geography files and the National Address Register. This does not constitute an endorsement by Statistics Canada of this product.
- Contains information licensed under the Open Government Licence – Canada (Innovation, Science and Economic Development Canada).
