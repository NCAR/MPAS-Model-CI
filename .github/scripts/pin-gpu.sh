#!/usr/bin/env bash
# Per-rank GPU pinning shim. Wrap your MPI binary like:
#   mpirun -n N <flags> bash pin-gpu.sh ./atmosphere_model
# Sets CUDA_VISIBLE_DEVICES to (local_rank % visible_gpu_count) per rank.
# Does nothing when no GPUs are detected (lets the model run as-is).
#
# Override knobs:
#   PIN_GPU_NGPU   force visible GPU count (skip detection)
#   PIN_GPU_DEBUG  set to 1 for verbose detection output
set -u

LOCAL_RANK="${MPI_LOCALRANKID:-${OMPI_COMM_WORLD_LOCAL_RANK:-${PMI_LOCAL_RANK:-${SLURM_LOCALID:-0}}}}"

NGPU="${PIN_GPU_NGPU:-}"
if [ -z "${NGPU}" ]; then
  if command -v nvidia-smi >/dev/null 2>&1; then
    NGPU=$(nvidia-smi -L 2>/dev/null | wc -l)
  fi
  if [ -z "${NGPU}" ] || [ "${NGPU}" -eq 0 ]; then
    NGPU=$(ls /dev/nvidia[0-9]* 2>/dev/null | wc -l)
  fi
fi

if [ -n "${NGPU}" ] && [ "${NGPU}" -gt 0 ]; then
  GPU_ID=$((LOCAL_RANK % NGPU))
  export CUDA_VISIBLE_DEVICES="${GPU_ID}"
  echo "[pin-gpu] rank=${LOCAL_RANK} -> GPU ${GPU_ID} (of ${NGPU})" >&2
else
  echo "[pin-gpu] no GPUs detected; not pinning (rank=${LOCAL_RANK})" >&2
fi

exec "$@"
