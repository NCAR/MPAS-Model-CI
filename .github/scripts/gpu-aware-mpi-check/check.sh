#!/bin/bash
# Does this container's MPI support GPU-aware (device-buffer) communication? Run INSIDE a GPU container on a GPU runner.
# usage: check.sh <mpich|openmpi>
# Prints static facts about the MPI/UCX build, builds devsend.f90 with the image's own nvfortran + MPI, and runs it on 2 ranks:
#   default       environment as shipped in the container
#   ci-env        exactly what the GPU workflows set for gpu-aware-mpi=true (.github/scripts/gpu-aware-mpi-env.sh)
#   control       GPU support switched OFF; this run is EXPECTED to fail (shows the test can detect missing support)
# Verdict: exit 0 iff the ci-env variant passes. Results go to $OUT (default gpu-aware-mpi-check-<mpi>) and $GITHUB_STEP_SUMMARY.
set -u
MPI="${1:?usage: check.sh <mpich|openmpi>}"
HERE="$(cd "$(dirname "$0")" && pwd)"; WS="${GITHUB_WORKSPACE:-$(cd "${HERE}/../../.." && pwd)}"
OUT="${OUT:-gpu-aware-mpi-check-${MPI}}"; mkdir -p "${OUT}"; OUT="$(cd "${OUT}" && pwd)"
[ -f /container/config_env.sh ] && source /container/config_env.sh
[ -f "${WS}/.github/ci-config.env" ] && source "${WS}/.github/ci-config.env"

BASE_FLAGS=""
[ "${MPI}" = openmpi ] && BASE_FLAGS="${OPENMPI_RUN_FLAGS:---allow-run-as-root --oversubscribe}"
[ "${MPI}" = mpich ] && BASE_FLAGS="${MPICH_RUN_FLAGS:-}"

{
  echo "== image: $(grep -h PRETTY_NAME /etc/os-release 2>/dev/null)"
  echo "== tools: $(command -v mpifort mpirun nvfortran 2>&1 | tr '\n' ' ')"
  echo "== GPU visible to the container:"; (nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>&1 || echo "nvidia-smi unavailable") | head -4
  if [ "${MPI}" = mpich ]; then
    echo "== mpichversion:"; mpichversion 2>&1 | grep -i -E "^MPICH Version|Device|Configure" | cut -c1-300
  else
    echo "== ompi_info:"; ompi_info --parsable 2>/dev/null | grep -E "ompi:version:full|mpi_built_with_cuda_support|mca:accelerator:[a-z]*:version|mca:pml:[a-z]*:version|mca:btl:smcuda:version" | cut -c1-150
  fi
  echo "== ucx:"; (ucx_info -v 2>&1 | head -3); echo "cuda lines in ucx_info -d: $(ucx_info -d 2>/dev/null | grep -i -c cuda)"
  echo "== libmpi links (cuda/ucx/fabric):"
  ldd "$(find "${MPI_ROOT:-/container/${MPI}}/lib" -name 'libmpi.so*' -type f 2>/dev/null | head -1)" 2>/dev/null | grep -i -E "cuda|ucx|fabric" | head -8
} > "${OUT}/static.txt" 2>&1

cd "${OUT}"
echo "== building devsend with $(command -v mpifort)"
if ! mpifort -acc -gpu=cc80,cc86 "${HERE}/devsend.f90" -o devsend > build.log 2>&1; then
  echo "::error::could not build the device-buffer test (see build.log)"; cat build.log | tail -20
  { echo "### GPU-aware MPI check (${MPI}): BUILD FAILED"; echo '```'; tail -20 build.log; echo '```'; } >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
  exit 2
fi

: > results.txt
run_variant() {   # $1 = name, $2 = shell setup evaluated in a subshell (may modify MPI_FLAGS / environment)
  local name="$1" setup="$2" log="run-$1.log" rc res
  ( MPI_FLAGS="${BASE_FLAGS}"; eval "${setup}"; echo "[${name}] mpirun -n 2 ${MPI_FLAGS} ./devsend"; timeout 150 mpirun -n 2 ${MPI_FLAGS} ./devsend ) > "${log}" 2>&1
  rc=$?
  res=FAIL; grep -q "DEVSEND RESULT: PASS" "${log}" && res=PASS; [ "${rc}" -eq 124 ] && res=TIMEOUT
  echo "${name}|${res}|${rc}" >> results.txt
  echo "---- ${name}: ${res} (exit ${rc})"; grep -a -v -E "^$" "${log}" | tail -3 | cut -c1-200
}
run_variant default "true"
run_variant ci-env  "MPI_IMPL=${MPI}; source '${WS}/.github/scripts/gpu-aware-mpi-env.sh'"
if [ "${MPI}" = mpich ]; then run_variant control "export MPIR_CVAR_ENABLE_GPU=0"
else run_variant control "export OMPI_MCA_accelerator=null"; fi

res() { awk -F'|' -v n="$1" '$1==n {print $2}' results.txt; }
D="$(res default)"; C="$(res ci-env)"; K="$(res control)"
{
  echo "### GPU-aware MPI check: ${MPI} container"
  echo ""; echo "| variant | result | exit |"; echo "|---|---|---|"
  awk -F'|' '{printf "| %s | %s | %s |\n", $1, $2, $3}' results.txt
  echo ""
  if [ "${C}" = PASS ]; then echo "**Verdict: the container MPI handles device buffers with the environment CI sets (ci-env PASS).**"
  else echo "**Verdict: NOT usable as configured (ci-env ${C}).**"; fi
  [ "${C}" != PASS ] && [ "${D}" = PASS ] && echo "" && echo "> The default environment passes but the CI environment fails: the settings in gpu-aware-mpi-env.sh are harmful for this MPI."
  [ "${K}" = PASS ] && echo "" && echo "> Control (GPU support off) also passed, so this test may not be sensitive to missing support."
  echo ""; echo "<details><summary>static facts</summary>"; echo ""; echo '```'; cat static.txt; echo '```'; echo "</details>"
} | tee summary.md >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
[ "${C}" = PASS ]
