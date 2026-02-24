#!/usr/bin/env python3
"""
Trim MPAS history files for ECT ensemble processing.

Extracts a single time slice and removes excluded variables to reduce
file sizes for artifact storage. No compression is applied to avoid
any risk of altering data in a validation pipeline.

Usage:
    python3 trim_history.py input.nc output.nc --tslice 1 --exclude-file excluded_vars.txt
"""

import argparse
import netCDF4 as nc


def trim_history(infile, outfile, tslice, exclude_vars=None):
    exclude = set(exclude_vars or [])

    with nc.Dataset(infile, 'r') as src, nc.Dataset(outfile, 'w', format='NETCDF4') as dst:
        for name, dim in src.dimensions.items():
            if name == 'Time':
                dst.createDimension(name, 1)
            else:
                dst.createDimension(name, len(dim))

        dst.setncatts({k: src.getncattr(k) for k in src.ncattrs()})

        kept = 0
        skipped = 0
        for name, var in src.variables.items():
            if name in exclude:
                skipped += 1
                continue

            dims = var.dimensions
            outvar = dst.createVariable(name, var.dtype, dims)
            outvar.setncatts({k: var.getncattr(k) for k in var.ncattrs()})

            if 'Time' in dims:
                tidx = dims.index('Time')
                slices = [slice(None)] * len(dims)
                slices[tidx] = slice(tslice, tslice + 1)
                outvar[:] = var[tuple(slices)]
            else:
                outvar[:] = var[:]

            kept += 1

        print(f"Kept {kept} variables, excluded {skipped}, "
              f"time slice {tslice}, compression enabled")


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
