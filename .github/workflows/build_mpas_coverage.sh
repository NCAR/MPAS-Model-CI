#!/usr/bin/env bash

set -ex

#----------------------------------------------------------------------------
# environment
SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${SCRIPTDIR}/build_common.cfg || { echo "cannot locate ${SCRIPTDIR}/build_common.cfg!!"; exit 1; }
#----------------------------------------------------------------------------

# Set up coverage compilation flags
export CFLAGS="${CFLAGS} -fprofile-arcs -ftest-coverage"
export CXXFLAGS="${CXXFLAGS} -fprofile-arcs -ftest-coverage"
export FCFLAGS="${FCFLAGS} -fprofile-arcs -ftest-coverage"
export LDFLAGS="${LDFLAGS} -lgcov"

echo "Building MPAS with coverage flags:"
echo "CFLAGS: $CFLAGS"
echo "CXXFLAGS: $CXXFLAGS"
echo "FCFLAGS: $FCFLAGS"
echo "LDFLAGS: $LDFLAGS"

# Create build directory
mkdir -p build
cd build

# Configure with CMake
cmake .. \
    -DCMAKE_BUILD_TYPE=Debug \
    -DUSE_PIO2=${USE_PIO2:-false} \
    -DPIO_ROOT=${PIO_ROOT:-/usr/local} \
    -DOPENACC=${OPENACC:-false}

# Build
make -j$(nproc) atmosphere_model

# Verify the executable was built
if [ ! -f atmosphere_model ]; then
    echo "ERROR: atmosphere_model executable not found!"
    exit 1
fi

echo "MPAS build completed successfully with coverage instrumentation" 