#!/bin/bash
# Build MPAS-Atmosphere out-of-tree: copy the source to a build dir, then `make <target>`.
help()
{
  echo "./build_mpas.sh [options]"
  echo "  -t   make target (gfortran, intel, nvhpc, ...)"
  echo "  -d   build directory (copy of the source tree is made here)"
  echo "  -p   precision: single|double (default double)"
  echo "  -j   make jobs (default 8)"
  echo "  -a   enable OpenACC (true|false, default false)"
  echo "  -f   fresh build: remove build dir first (true|false, default true)"
}

precision=double; jobs=8; acc=false; fresh=true
while getopts t:d:p:j:a:f:h opt; do
  case $opt in
    t) target="$OPTARG" ;;
    d) builddir="$OPTARG" ;;
    p) precision="$OPTARG" ;;
    j) jobs="$OPTARG" ;;
    a) acc="$OPTARG" ;;
    f) fresh=$( echo "$OPTARG" | tr '[:upper:]' '[:lower:]' ) ;;
    h) help; exit 0 ;;
    *) help; exit 1 ;;
  esac
done

if [ -z "$target" ] || [ -z "$builddir" ]; then help; exit 1; fi

[ "$fresh" = "true" ] && rm -rf "$builddir"
mkdir -p "$builddir"
echo "Copying MPAS source to $builddir"
# --exclude keeps build dirs (including this one if nested) and VCS data out of the copy
tar -cf - --exclude=.git --exclude='_build_*' --exclude='.sane' --exclude='*.o' --exclude='*.mod' . | tar -xf - -C "$builddir"
cd "$builddir" || exit 1

echo "Compiler: $(mpif90 --version 2>&1 | head -1)  NETCDF=$NETCDF  PNETCDF=$PNETCDF"
make "$target" CORE=atmosphere PRECISION="$precision" OPENACC="$acc" --jobs "$jobs"
if [ $? -ne 0 ] || [ ! -x ./atmosphere_model ]; then
  echo "Failed to build atmosphere_model"
  exit 1
fi
echo "Built $(pwd)/atmosphere_model"
