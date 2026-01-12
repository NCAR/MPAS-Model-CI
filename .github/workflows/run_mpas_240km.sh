#!/usr/bin/env bash

set -ex

#----------------------------------------------------------------------------
# environment
SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source ${SCRIPTDIR}/build_common.cfg || { echo "cannot locate ${SCRIPTDIR}/build_common.cfg!!"; exit 1; }
#----------------------------------------------------------------------------

# Accept arguments:
# $1: number of processors (default: 1 or NUM_PROCS env var)
# $2: run duration in format "DD_HH:MM:SS" (default: RUN_DURATION env var or "0_06:00:00")
# $3: restart output interval in format "DD_HH:MM:SS" (default: RESTART_INTERVAL env var or "0_06:00:00")
NUM_PROCS="${1:-${NUM_PROCS:-1}}"
RUN_DURATION="${2:-${RUN_DURATION:-0_06:00:00}}"
RESTART_INTERVAL="${3:-${RESTART_INTERVAL:-0_06:00:00}}"

tar xzf .github/workflows/240km.tar.gz
mv 240km 240km_${NUM_PROCS}
cd 240km_${NUM_PROCS}/

ln -sf ../atmosphere_model .

# Modify namelist.atmosphere to change run duration (config_run_duration) 
sed -i "s/config_run_duration = '[^']*'/config_run_duration = '${RUN_DURATION}'/" namelist.atmosphere

# Modify streams.atmosphere to change restart output_interval
sed -i '/<immutable_stream name="restart"/,/\/>/ s/output_interval="[^"]*"/output_interval="'${RESTART_INTERVAL}'"/' streams.atmosphere


echo "Running MPAS from $(pwd) on $NUM_PROCS processors"
echo "Run duration: $RUN_DURATION"
echo "Restart interval: $RESTART_INTERVAL"
echo "MPI_FLAGS: $MPI_FLAGS"

# Run the model with MPI flags
# Use pipefail to ensure the script fails if mpirun fails
set -o pipefail

mpirun -n "$NUM_PROCS" $MPI_FLAGS ./atmosphere_model

