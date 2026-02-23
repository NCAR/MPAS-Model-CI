#!/usr/bin/env bash

set -ex

#----------------------------------------------------------------------------
# Generic MPAS-A test case runner
#
# Usage: run_mpas.sh <resolution> [num_procs] [run_duration] [restart_interval]
#
# Arguments:
#   resolution       - Test case name (e.g., 240km, 120km). Must have a
#                      corresponding config at .github/test-cases/<resolution>/config.env
#   num_procs        - Number of MPI processes (default: 1 or NUM_PROCS env var)
#   run_duration     - Override run duration (format: D_HH:MM:SS)
#   restart_interval - Override restart interval (format: D_HH:MM:SS)
#
# Environment variables:
#   MPI_IMPL         - MPI implementation (openmpi, mpich)
#   MPI_FLAGS        - Additional MPI flags
#   NUM_PROCS        - Default number of processors
#   RUN_DURATION     - Default run duration
#   RESTART_INTERVAL - Default restart interval
#----------------------------------------------------------------------------

#----------------------------------------------------------------------------
# environment
SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
REPODIR="$( cd "${SCRIPTDIR}/../.." && pwd )"
source ${SCRIPTDIR}/build_common.cfg || { echo "cannot locate ${SCRIPTDIR}/build_common.cfg!!"; exit 1; }
#----------------------------------------------------------------------------

# Parse arguments
RESOLUTION="${1:?Error: resolution argument required (e.g., 240km)}"
shift

# Load test case configuration
CONFIG_FILE="${REPODIR}/.github/test-cases/${RESOLUTION}/config.env"
if [ -f "${CONFIG_FILE}" ]; then
    echo "Loading configuration from ${CONFIG_FILE}"
    source "${CONFIG_FILE}"
else
    echo "Warning: No config file found at ${CONFIG_FILE}, using defaults"
fi

# Apply argument overrides (command-line > env var > config file)
NUM_PROCS="${1:-${NUM_PROCS:-1}}"
RUN_DURATION="${2:-${RUN_DURATION:-0_06:00:00}}"
RESTART_INTERVAL="${3:-${RESTART_INTERVAL:-0_06:00:00}}"

DATA_REPO="${DATA_REPO:-NCAR/mpas-ci-data}"

#----------------------------------------------------------------------------
# Set MPI flags based on implementation
#----------------------------------------------------------------------------
if [ "${MPI_IMPL}" = "openmpi" ]; then
    MPI_FLAGS="${MPI_FLAGS} --allow-run-as-root"
fi

#----------------------------------------------------------------------------
# Download and extract test case
#----------------------------------------------------------------------------
ARCHIVE="${RESOLUTION}.tar.gz"
if [ ! -f "${ARCHIVE}" ]; then
    echo "Downloading ${ARCHIVE} from ${DATA_REPO}..."
    curl -fsSL "https://github.com/${DATA_REPO}/raw/main/${ARCHIVE}" -o "${ARCHIVE}"
    echo "Downloaded $(du -h "${ARCHIVE}" | cut -f1) archive"
fi

tar xzf "${ARCHIVE}"

# Get the extracted directory name
CASE_DIR=$(tar tzf "${ARCHIVE}" 2>/dev/null | head -1 | cut -d/ -f1 || true)
if [ -z "${CASE_DIR}" ]; then
    echo "ERROR: Could not determine extracted directory name"
    exit 1
fi

# Rename to include proc count for parallel runs
RUN_DIR="${RESOLUTION}_${NUM_PROCS}"
mv "${CASE_DIR}" "${RUN_DIR}"
cd "${RUN_DIR}/"

ln -sf ../atmosphere_model .

#----------------------------------------------------------------------------
# Configure namelist and streams
#----------------------------------------------------------------------------
sed -i "s/config_run_duration = '[^']*'/config_run_duration = '${RUN_DURATION}'/" namelist.atmosphere
sed -i '/<immutable_stream name="restart"/,/\/>/ s/output_interval="[^"]*"/output_interval="'"${RESTART_INTERVAL}"'"/' streams.atmosphere

#----------------------------------------------------------------------------
# Run the model
#----------------------------------------------------------------------------
echo "Running MPAS from $(pwd) on $NUM_PROCS processors"
echo "  Resolution:       ${RESOLUTION}"
echo "  Run duration:     ${RUN_DURATION}"
echo "  Restart interval: ${RESTART_INTERVAL}"
echo "  MPI_FLAGS:        ${MPI_FLAGS}"

# Set unlimited stack size to prevent stack overflow issues
ulimit -s unlimited 2>/dev/null || echo "Warning: Could not set unlimited stack size"
echo "  Stack size limit: $(ulimit -s)"

# Run the model with MPI flags
set -o pipefail
mpirun -n "$NUM_PROCS" $MPI_FLAGS ./atmosphere_model
