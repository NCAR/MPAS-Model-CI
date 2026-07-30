#!/usr/bin/env python3
"""Compare two NetCDF files for bitwise-identical variable *data*.

NetCDF files from PIO vs SMIOL or different MPI layouts often differ in headers,
attributes, or chunking while variable arrays remain identical — `cmp` is too strict.
"""
from __future__ import annotations

import sys

import netCDF4 as nc
import numpy as np


def as_array(x):
    if np.ma.isMaskedArray(x):
        return np.ma.filled(x)
    return np.asarray(x)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: compare-bfb-nc.py <reference.nc> <candidate.nc>", file=sys.stderr)
        return 2
    path_ref, path_test = sys.argv[1], sys.argv[2]
    diffs: list[str] = []
    with nc.Dataset(path_ref) as ds_ref, nc.Dataset(path_test) as ds_test:
        vr = set(ds_ref.variables)
        vt = set(ds_test.variables)
        if vr != vt:
            only_r = sorted(vr - vt)
            only_t = sorted(vt - vr)
            print(
                "FAIL\t"
                f"variable set mismatch: only in reference {only_r}, only in candidate {only_t}"
            )
            return 1
        for name in sorted(vr):
            a = as_array(ds_ref.variables[name][:])
            b = as_array(ds_test.variables[name][:])
            if a.shape != b.shape:
                diffs.append(f"{name}: shape {a.shape} vs {b.shape}")
                continue
            if not np.array_equal(a, b):
                if np.issubdtype(a.dtype, np.floating) or np.issubdtype(
                    a.dtype, np.complexfloating
                ):
                    maxdiff = float(np.max(np.abs(a - b)))
                    diffs.append(f"{name} (max|diff|={maxdiff:.6e})")
                else:
                    diffs.append(f"{name} (data differs)")
    if diffs:
        msg = "; ".join(diffs[:25])
        print(f"FAIL\t{msg}")
        if len(diffs) > 25:
            print(f"... and {len(diffs) - 25} more", file=sys.stderr)
        return 1
    print("OK\tall variables bitwise-identical (NetCDF container/metadata may differ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
