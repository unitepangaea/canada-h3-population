"""Example local path overrides for src/config.py.

Copy this file to src/config_local.py (excluded from git) and set only the names you need.
Any upper-case path name defined in config.py can be set here. Names left out keep their
defaults, which are folders at the repository root (data_raw/, data_int/, output_v2/,
tables/, figures/).
"""
from pathlib import Path

# Folder holding the downloaded inputs, if not <repo>/data_raw
# DATA_RAW = Path("/path/to/hexpop_inputs")

# Large intermediate and output folders, for example on an external drive
# DATA_INT = Path("/path/to/scratch/data_int")
# OUTPUT_V2 = Path("/path/to/scratch/output_v2")

# A single input kept somewhere else
# NAR_DIR = Path("/path/to/NAR-202606")
