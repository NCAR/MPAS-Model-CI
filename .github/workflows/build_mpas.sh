#!/usr/bin/env bash

set -ex

#----------------------------------------------------------------------------
# environment
SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${SCRIPTDIR}/build_common.cfg || { echo "cannot locate ${SCRIPTDIR}/build_common.cfg!!"; exit 1; }
#----------------------------------------------------------------------------


echo "building MPAS-A in $(pwd)"

case "${COMPILER_FAMILY}" in
    "aocc"|"clang")
        compiler_target="llvm"
        ;;
    "gcc")
        compiler_target="gfortran"
        ;;
    "oneapi")
        compiler_target="intel"
        ;;
    "nvhpc")
        compiler_target="nvhpc"
        ;;
    *)
        echo "ERROR: unrecognized COMPILER_FAMILY=${COMPILER_FAMILY}"!
        exit 1
        ;;
esac



make ${compiler_target} CORE=atmosphere --jobs ${MAKE_J_PROCS:-$(nproc)}
