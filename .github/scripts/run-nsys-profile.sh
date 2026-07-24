#!/usr/bin/env bash
# Run MPAS-A under Nsight Systems (nsys profile). Intended for CIRRUS GPU CI.
# Usage: run-nsys-profile.sh <workdir> <num-procs> <mpi-impl> <timeout-minutes> <nsys-output-basename>
set -euo pipefail

WORKDIR="${1:?workdir required}"
NUM_PROCS="${2:?num-procs required}"
MPI_IMPL="${3:?mpi-impl required}"
TIMEOUT="${4:?timeout minutes required}"
NSYS_BASENAME="${5:?nsys output basename required}"

if [ -f /container/config_env.sh ]; then
  # shellcheck source=/dev/null
  source /container/config_env.sh
fi

if [ -z "${LD_LIBRARY_PATH:-}" ]; then
  export LD_LIBRARY_PATH="/usr/lib64:/usr/lib"
fi

REPO_ROOT="${GITHUB_WORKSPACE:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
CI_CONFIG="${REPO_ROOT}/.github/ci-config.env"
if [ -f "${CI_CONFIG}" ]; then
  # shellcheck source=/dev/null
  source "${CI_CONFIG}"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/resolve-nsys.sh"

if ! resolve_nsys; then
  echo "::error::No working nsys found. NVHPC may expose a stub that fails with Nsight version errors;"
  echo "::error::install a full Nsight Systems build under /opt/nvidia/nsight-systems or ensure CUDA toolkit nsys is on PATH."
  exit 1
fi

echo "=== nsys (${NSYS_BIN}) ==="
"${NSYS_BIN}" --version

if [ -n "${GITHUB_ENV:-}" ]; then
  {
    echo "NSYS_BIN=${NSYS_BIN}"
  } >> "${GITHUB_ENV}"
fi

MPI_FLAGS=""
if [ "${MPI_IMPL}" = "openmpi" ]; then
  MPI_FLAGS="${OPENMPI_RUN_FLAGS:---allow-run-as-root --oversubscribe}"
fi

ulimit -s unlimited 2>/dev/null || true

cd "${WORKDIR}"

OUT_ABS="${PWD}/${NSYS_BASENAME}"
echo "=== Nsight profile ==="
echo "  workdir: ${WORKDIR}"
echo "  ranks:   ${NUM_PROCS}"
echo "  mpi:     ${MPI_IMPL}"
echo "  output:  ${OUT_ABS}"
echo "  timeout: ${TIMEOUT}m"

set +e
timeout "${TIMEOUT}"m "${NSYS_BIN}" profile \
  --trace=cuda,nvtx,osrt \
  --stats=true \
  -o "${OUT_ABS}" \
  mpirun -n "${NUM_PROCS}" ${MPI_FLAGS} ./atmosphere_model
RUN_STATUS=$?
set -e

if [ "${RUN_STATUS}" -ne 0 ]; then
  echo "::warning::Profiled run exited with status ${RUN_STATUS}"
  exit "${RUN_STATUS}"
fi

echo "=== nsys profile finished ==="
ls -la "${NSYS_BASENAME}".* 2>/dev/null || ls -la ./*.nsys-rep 2>/dev/null || true
