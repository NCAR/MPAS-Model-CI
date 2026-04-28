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

# Opt-in CUDA-aware MPI: passes device pointers to MPI without host staging.
# Requires the container's MPI library to be built with GPU support; if it
# isn't, MPI will either silently fall back to host staging or abort.
CUDA_AWARE_MPI="${CUDA_AWARE_MPI:-false}"
if [ "${CUDA_AWARE_MPI}" = "true" ]; then
  case "${MPI_IMPL}" in
    mpich)
      export MPICH_GPU_SUPPORT_ENABLED=1
      ;;
    openmpi)
      export OMPI_MCA_pml=ucx
      export OMPI_MCA_osc=ucx
      export UCX_TLS=cuda,cuda_copy,cuda_ipc,sm,self
      MPI_FLAGS="${MPI_FLAGS} --mca pml ucx --mca osc ucx"
      ;;
  esac
fi

ulimit -s unlimited 2>/dev/null || true

cd "${WORKDIR}"

OUT_ABS="${PWD}/${NSYS_BASENAME}"
echo "=== Nsight profile ==="
echo "  workdir:        ${WORKDIR}"
echo "  ranks:          ${NUM_PROCS}"
echo "  mpi:            ${MPI_IMPL}"
echo "  cuda-aware mpi: ${CUDA_AWARE_MPI}"
echo "  output:         ${OUT_ABS}"
echo "  timeout:        ${TIMEOUT}m"

# Trace MPI alongside CUDA so halo exchanges show up in the timeline and we
# can tell device-to-device transfers from host-staged ones.
# pin-gpu.sh sets CUDA_VISIBLE_DEVICES per rank so multi-rank runs spread
# across the node's GPUs instead of stacking on device 0.
set +e
timeout "${TIMEOUT}"m "${NSYS_BIN}" profile \
  --trace=cuda,nvtx,osrt,mpi \
  --stats=true \
  -o "${OUT_ABS}" \
  mpirun -n "${NUM_PROCS}" ${MPI_FLAGS} bash "${SCRIPT_DIR}/pin-gpu.sh" ./atmosphere_model
RUN_STATUS=$?
set -e

if [ "${RUN_STATUS}" -ne 0 ]; then
  echo "::warning::Profiled run exited with status ${RUN_STATUS}"
  exit "${RUN_STATUS}"
fi

echo "=== nsys profile finished ==="
ls -la "${NSYS_BASENAME}".* 2>/dev/null || ls -la ./*.nsys-rep 2>/dev/null || true
