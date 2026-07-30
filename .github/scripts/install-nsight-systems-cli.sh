#!/usr/bin/env bash
# Install NVIDIA Nsight Systems CLI (nsys) on RHEL/Alma/Rocky via the devtools repo.
# Idempotent: skips if resolve-nsys.sh already finds a working nsys.
# Optional: NSYS_RPM_CACHE_DIR — directory to store .rpm files for actions/cache.
#
# shellcheck shell=bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/resolve-nsys.sh"

_emit_github_env() {
  if [ -n "${GITHUB_ENV:-}" ] && [ -n "${NSYS_BIN:-}" ]; then
    {
      echo "NSYS_BIN=${NSYS_BIN}"
      echo "PATH=${PATH}"
    } >> "${GITHUB_ENV}"
  fi
}

if resolve_nsys; then
  echo "=== nsys already usable: ${NSYS_BIN} ==="
  "${NSYS_BIN}" --version
  _emit_github_env
  exit 0
fi

echo "=== Installing nsight-systems-cli (NVIDIA devtools repo) ==="

if ! command -v dnf &>/dev/null; then
  echo "::error::dnf not found; this installer supports RHEL-family GPU images only."
  exit 1
fi

# GPG key used by NVIDIA CUDA / devtools RPM repos (RHEL 9)
if [ -f /etc/os-release ]; then
  # shellcheck source=/dev/null
  source /etc/os-release
else
  echo "::error::Cannot read /etc/os-release"
  exit 1
fi

RHEL_VER="${VERSION_ID%%.*}"
ARCH_DIR="$(rpm --eval '%{_arch}' | sed 's/aarch/arm/')"
REPO_BASE="https://developer.download.nvidia.com/devtools/repos/rhel${RHEL_VER}/${ARCH_DIR}/"

for key in \
  "https://developer.download.nvidia.com/compute/cuda/repos/rhel${RHEL_VER}/x86_64/D42D0685.pub" \
  "https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/7fa2af80.pub"
do
  if rpm --import "${key}" 2>/dev/null; then
    break
  fi
done

# Same repo layout as Nsight Systems Installation Guide (RHEL / Alma / Rocky).
cat > /etc/yum.repos.d/nvidia-devtools-ci.repo <<EOF
[nvidia-devtools-ci]
name=NVIDIA Developer Tools
baseurl=${REPO_BASE}
enabled=1
gpgcheck=0
EOF
dnf makecache -y || true

RPM_CACHE="${NSYS_RPM_CACHE_DIR:-}"
if [ -n "${RPM_CACHE}" ]; then
  mkdir -p "${RPM_CACHE}"
fi

shopt -s nullglob
RPM_FILES=( )
if [ -n "${RPM_CACHE}" ]; then
  RPM_FILES=( "${RPM_CACHE}"/*.rpm )
fi
shopt -u nullglob

if [ -n "${RPM_CACHE}" ] && [ "${#RPM_FILES[@]}" -gt 0 ]; then
  echo "=== Installing from cached RPMs in ${RPM_CACHE} (${#RPM_FILES[@]} files) ==="
  dnf install -y "${RPM_FILES[@]}"
else
  echo "=== Downloading nsight-systems-cli RPMs ==="
  if [ -n "${RPM_CACHE}" ]; then
    dnf install -y --downloadonly --downloaddir="${RPM_CACHE}" nsight-systems-cli
    shopt -s nullglob
    RPM_FILES=( "${RPM_CACHE}"/*.rpm )
    shopt -u nullglob
    if [ "${#RPM_FILES[@]}" -eq 0 ]; then
      echo "::error::dnf --downloadonly did not produce RPMs in ${RPM_CACHE}"
      exit 1
    fi
    echo "=== Installing from ${RPM_CACHE} (${#RPM_FILES[@]} RPMs) ==="
    dnf install -y "${RPM_FILES[@]}"
  else
    dnf install -y nsight-systems-cli
  fi
fi

# Prefer the RPM-provided nsys over any NVHPC stub on PATH
if command -v rpm &>/dev/null; then
  while IFS= read -r cand; do
    if [ -x "${cand}" ] && "${cand}" --version &>/dev/null; then
      export NSYS_BIN="${cand}"
      export PATH="$(dirname "${cand}"):${PATH}"
      echo "=== Pinned NSYS_BIN to RPM path: ${NSYS_BIN} ==="
      break
    fi
  done < <(rpm -ql nsight-systems-cli 2>/dev/null | grep -E '/nsys$' || true)
fi

if ! resolve_nsys; then
  echo "::error::nsight-systems-cli did not yield a working nsys. Check NVIDIA repo and image OS version."
  exit 1
fi

echo "=== nsys ready: ${NSYS_BIN} ==="
"${NSYS_BIN}" --version
_emit_github_env
