"""Single configuration for the v2 multi-resolution pipeline (protocol Section 4, B1).

Every path is relative to the repository root (BASE). By default the pipeline reads inputs
from data_raw/ and writes to data_int/, output_v2/, tables/ and figures/, all at the root and
all excluded from git. No paths need to be edited.

To keep inputs or outputs elsewhere, copy config_local_example.py to config_local.py (also
excluded from git) and set any of the upper-case path names below in it.
Column names are copied from 01_final_pipeline/.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
BASE = Path(__file__).resolve().parents[1]          # repository root

try:                                                 # optional, git-ignored overrides
    import config_local as _cl
    _LOCAL = {k: Path(v) for k, v in vars(_cl).items() if k.isupper() and isinstance(v, (str, Path))}
except ImportError:
    _LOCAL = {}

# Top-level folders
DATA_RAW = _LOCAL.get("DATA_RAW", BASE / "data_raw")      # downloaded inputs (docs/PROVENANCE.md)
DATA_INT = _LOCAL.get("DATA_INT", BASE / "data_int")      # intermediate files from 01 and a4
OUTPUT_V2 = _LOCAL.get("OUTPUT_V2", BASE / "output_v2")   # layers from 02 and 03
TABLES = _LOCAL.get("TABLES", BASE / "tables")            # tables from 04 to 08
FIGURES_V2 = _LOCAL.get("FIGURES_V2", BASE / "figures")   # figures from 07
REFERENCE_V1 = _LOCAL.get("REFERENCE_V1", DATA_RAW / "reference_v1")  # preprint outputs (Phase C only)

# Inputs, as unpacked from the downloads listed in docs/PROVENANCE.md
GAF_CSV = DATA_RAW / "GAF2021.csv"
DB_CARTO_SHP = DATA_RAW / "ldb_000b21a_e" / "ldb_000b21a_e.shp"
DB_DIGITAL_SHP = DATA_RAW / "ldb_000a21a_e" / "ldb_000a21a_e.shp"
PHH_DIR = DATA_RAW / "phh_2021" / "PHH_2021_CSV"
NAR_DIR = DATA_RAW / "NAR-202606"
DA_CARTO_SHP = DATA_RAW / "lda_000b21a_e" / "lda_000b21a_e.shp"
PC_CARTO_SHP = DATA_RAW / "lpc_000b21a_e" / "lpc_000b21a_e.shp"
PROV_GPKG = DATA_RAW / "province_boundaries.gpkg"          # figures only

# Intermediate files
NAR_LOCATIONS = DATA_INT / "nar_locations_v2.parquet"      # Phase A4
PHH_POINTS = DATA_INT / "phh_points.parquet"               # 01_prepare_points
NAR_POINTS = DATA_INT / "nar_points.parquet"               # 01_prepare_points
DB_CARTO_4326 = DATA_INT / "db_carto_4326.parquet"         # 01_prepare_points
DB_DIGITAL_4326 = DATA_INT / "db_digital_4326.parquet"     # 01_prepare_points

# Preprint (method v1) reference outputs, read only by c_reproduce_preprint.py
PREPRINT_COMPARISON_GPKG = REFERENCE_V1 / "h3_method_comparison.gpkg"
PREPRINT_HYBRID_GPKG = REFERENCE_V1 / "hybrid_h3_population_canada.gpkg"
PREPRINT_TABLE3_CSV = REFERENCE_V1 / "table3_corrected.csv"
PREPRINT_SWEEP_CSV = REFERENCE_V1 / "threshold_sweep_results.csv"

# Any other upper-case name set in config_local.py (for example a single input file) wins
globals().update({k: v for k, v in _LOCAL.items() if k in globals()})


def rel(p: Path) -> str:
    """Path for log messages: relative to the repository when inside it, absolute otherwise."""
    p = Path(p)
    try:
        return str(p.resolve().relative_to(BASE))
    except ValueError:
        return str(p)


MAP_CRS = "EPSG:3347"           # NAD83 / Statistics Canada Lambert (Lambert Conformal Conic) for every map

# ----------------------------------------------------------------------------
# Analysis settings
# ----------------------------------------------------------------------------
RESOLUTIONS = [6, 7, 8]
TAUS = [5, 10, 20, 50, 100]
FINAL_TAU = 50

METHOD_VERSION = "v2"           # default for run_all; "v1" reproduces the preprint
HEADLINE_VARIANT = "base"       # GATE D (2026-11-06): base v2 is the headline hybrid; HYB-V is a sensitivity layer
USE_BU_FILTER = True            # per method version, see METHODS
BU_KEEP = {1, 2}
BU_KEEP_SENSITIVITY = {1, 2, 4}
PIP_BOUNDARY = "digital"        # "cartographic" or "digital", per method version

VINTAGE_GAMMA = 1.5
VINTAGE_GAMMAS_SENS = [1.25, 2.0]
VINTAGE_MIN_EXCESS = 10

CRS_AREA = "ESRI:102001"        # Canada Albers equal-area (Eq. 1)
CRS_VARIANTS = {                # D3 exports, as in the preprint
    "nad83_geographic": "EPSG:4269",
    "albers_equal_area": "ESRI:102001",
    "statcan_lambert": "EPSG:3347",
}
CA_LAT_RANGE = (41, 84)
CA_LON_RANGE = (-142, -52)

LOW_COUNT_THRESHOLD = 5         # low_count_flag: population < 5 (F7 uses 5, 10, 50)

# Populated GAF DBs with no polygon in the cartographic file (water-only DBs, 5 people each).
# Decision 2026-11-06: P = 36,991,971 for every method version, so these are outside the
# DB universe. The universe is the set of DBs with a cartographic polygon (498,547 DBs).
EXCLUDED_DBUIDS = {"10020079053", "59430125042"}
EXPECTED_P = 36_991_971
EXPECTED_POPULATED_DBS = 384_284

# ----------------------------------------------------------------------------
# Column names (from 01_final_pipeline)
# ----------------------------------------------------------------------------
GAF_DBUID_COL = "DBUID_IDIDU"
GAF_POP_COL = "DBPOP2021_IDPOP2021"
GAF_COLS = {
    "DBUID_IDIDU": "DBUID",
    "DBPOP2021_IDPOP2021": "POP",
    "DBTDWELL2021_IDTLOG2021": "DB_TDWELL",
    "DBAREA2021_IDSUP2021": "DB_LANDAREA_KM2",
    "PRUID_PRIDU": "PR",
    "CSDUID_SDRIDU": "CSDUID",
    "CSDNAME_SDRNOM": "CSDNAME",
    "CMAUID_RMRIDU": "CMAUID",
    "CMAPUID_RMRPIDU": "CMAPUID",
    "CMANAME_RMRNOM": "CMANAME",
    "POPCTRRAPUID_CTRPOPRRPIDU": "POPCTRRAPUID",
    "POPCTRRANAME_CTRPOPRRNOM": "POPCTRRANAME",
    "POPCTRRACLASS_CTRPOPRRCLASSE": "POPCTRRACLASS",
    "DAUID_ADIDU": "DAUID",
}
DB_SHP_DBUID_COL = "DBUID"
PHH_COLS = {
    "DBUID_Ididu": "DBUID",
    "Pruid_Pridu": "PR",
    "Pop2021": "pop",
    "TDwell2021_TLog2021": "dwell_total",
    "URDwell2021_RH2021": "dwell_occ",
    "Type": "type",
    "Latitude": "lat",
    "Longitude": "lon",
}
NAR_LAT_COL = "BF_REPPOINT_LATITUDE"
NAR_LON_COL = "BF_REPPOINT_LONGITUDE"


# ----------------------------------------------------------------------------
# Method versions and variants
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class RunSettings:
    method: str
    variant: str
    use_bu_filter: bool
    bu_keep: frozenset
    pip_boundary: str
    hyb_v: bool
    phh_include_unpolygoned: bool

    @property
    def tag(self) -> str:
        return self.method if self.variant == "base" else f"{self.method}_{self.variant}"

    @property
    def out_dir(self) -> Path:
        return OUTPUT_V2 / self.tag

    def res_dir(self, r: int) -> Path:
        return self.out_dir / f"res{r}"

    @property
    def dbuid_col(self) -> str:
        return {"cartographic": "DBUID_carto", "digital": "DBUID_digital"}[self.pip_boundary]


# v1 = preprint. The preprint's standalone PHH layer summed every PHH point, including the
# 10 people in EXCLUDED_DBUIDS, so v1 keeps them in the PHH layer only (needed for GATE C).
METHODS = {
    "v1":    dict(use_bu_filter=False, pip_boundary="cartographic", phh_include_unpolygoned=True),
    "v1_M1": dict(use_bu_filter=True,  pip_boundary="cartographic", phh_include_unpolygoned=False),
    "v1_M2": dict(use_bu_filter=False, pip_boundary="digital",      phh_include_unpolygoned=False),
    "v2":    dict(use_bu_filter=True,  pip_boundary="digital",      phh_include_unpolygoned=False),
}
VARIANTS = ["base", "bu124", "hybv"]


def settings(method: str = METHOD_VERSION, variant: str = "base") -> RunSettings:
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}; choose from {list(METHODS)}")
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; choose from {VARIANTS}")
    m = METHODS[method]
    if variant == "bu124" and not m["use_bu_filter"]:
        raise ValueError("variant bu124 needs a method with the BU filter on")
    return RunSettings(
        method=method,
        variant=variant,
        use_bu_filter=m["use_bu_filter"],
        bu_keep=frozenset(BU_KEEP_SENSITIVITY if variant == "bu124" else BU_KEEP),
        pip_boundary=m["pip_boundary"],
        hyb_v=variant == "hybv",
        phh_include_unpolygoned=m["phh_include_unpolygoned"],
    )
