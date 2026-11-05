#!/usr/bin/env python3
"""Exit 1 if any floating-point variable in the given NetCDF files contains NaN."""
import sys
import numpy as np
from netCDF4 import Dataset

bad = 0
for path in sys.argv[1:]:
    with Dataset(path) as ds:
        for name, var in ds.variables.items():
            if var.dtype.kind != "f":
                continue
            n = int(np.isnan(np.ma.filled(var[:].astype(float), 0.0)).sum())
            if n:
                print(f"::error::{path}: {name} has {n} NaN value(s)")
                bad += 1
    print(f"checked {path}")
sys.exit(1 if bad else 0)
