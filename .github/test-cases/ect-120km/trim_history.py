#!/usr/bin/env python3
"""
Trim MPAS history files for ECT ensemble processing.

Extracts a single time slice, removes excluded variables, strips static
mesh geometry (identical across ensemble members), and applies lossless
NetCDF4 deflation (zlib) to minimize artifact sizes.

Usage:
    python3 trim_history.py input.nc output.nc --tslice 0 --exclude-file excluded_vars.txt
"""

import argparse
import os
import netCDF4 as nc


def trim_history(infile, outfile, tslice, exclude_vars=None):
    exclude = set(exclude_vars or [])

    with nc.Dataset(infile, 'r') as src, nc.Dataset(outfile, 'w', format='NETCDF4') as dst:
        # Only create dimensions that appear in kept variables.
        # We'll add them lazily below.
        needed_dims = set()

        dst.setncatts({k: src.getncattr(k) for k in src.ncattrs()})

        # First pass: identify which variables to keep (time-varying only)
        keep = {}
        for name, var in src.variables.items():
            if name in exclude:
                continue
            if 'Time' not in var.dimensions:
                continue
            keep[name] = var
            needed_dims.update(var.dimensions)

        # Create only the dimensions used by kept variables
        for dname in needed_dims:
            if dname == 'Time':
                dst.createDimension(dname, 1)
            else:
                dst.createDimension(dname, len(src.dimensions[dname]))

        kept = 0
        for name, var in keep.items():
            dims = var.dimensions
            use_zlib = var.size > 1000
            outvar = dst.createVariable(
                name, var.dtype, dims,
                zlib=use_zlib, complevel=1)
            outvar.setncatts({k: var.getncattr(k) for k in var.ncattrs()})

            tidx = dims.index('Time')
            slices = [slice(None)] * len(dims)
            slices[tidx] = slice(tslice, tslice + 1)
            outvar[:] = var[tuple(slices)]
            kept += 1

        skipped = len(src.variables) - kept

    in_size = os.path.getsize(infile) / 1048576
    out_size = os.path.getsize(outfile) / 1048576
    print(f"Kept {kept} time-varying variables, dropped {skipped} "
          f"(static mesh + excluded), tslice={tslice}, "
          f"{in_size:.0f}MB -> {out_size:.0f}MB")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Trim MPAS history files for ECT')
    parser.add_argument('input', help='Input history file')
    parser.add_argument('output', help='Output trimmed file')
    parser.add_argument('--tslice', type=int, default=0,
                        help='Time slice index to extract')
    parser.add_argument('--exclude-file',
                        help='File listing variable names to exclude')
    args = parser.parse_args()

    exclude = []
    if args.exclude_file:
        with open(args.exclude_file) as f:
            exclude = [line.strip() for line in f
                       if line.strip() and not line.startswith('#')]

    trim_history(args.input, args.output, args.tslice, exclude)
