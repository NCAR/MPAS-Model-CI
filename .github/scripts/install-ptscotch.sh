#!/usr/bin/env bash
# Build and install PT-SCOTCH (static libs) from the official source tarball.
# Idempotent: skips the build if a usable install is already at PREFIX.
#
# Required env:
#   SCOTCH_VERSION  - release tag, e.g. 7.0.4
#   SCOTCH_PREFIX   - install prefix (Makefile expects $SCOTCH/include and $SCOTCH/lib64)
#
# shellcheck shell=bash
set -euo pipefail

: "${SCOTCH_VERSION:?SCOTCH_VERSION not set}"
: "${SCOTCH_PREFIX:?SCOTCH_PREFIX not set}"

# Container images put the compiler/MPI toolchain on PATH via this script
# (same as build-mpas). Without it, cmake can fail to find a C compiler at all
# ("CMAKE_C_COMPILER not set, after EnableLanguage").
if [ -f /container/config_env.sh ]; then
  echo "Sourcing container environment from /container/config_env.sh"
  # shellcheck source=/dev/null
  source /container/config_env.sh
fi

if [ -f "${SCOTCH_PREFIX}/include/ptscotch.h" ] && [ -f "${SCOTCH_PREFIX}/lib64/libptscotch.a" ]; then
  echo "=== PT-SCOTCH already installed at ${SCOTCH_PREFIX} (cache hit) ==="
  exit 0
fi

echo "=== Installing build dependencies (cmake) ==="
if ! command -v cmake &>/dev/null; then
  if command -v dnf &>/dev/null; then
    dnf install -y cmake
  elif command -v zypper &>/dev/null; then
    zypper install -y --no-recommends cmake
  elif command -v apt-get &>/dev/null; then
    apt-get update && apt-get install -y cmake
  else
    echo "::error::No supported package manager found to install cmake."
    exit 1
  fi
fi
cmake --version

if ! command -v mpicc &>/dev/null; then
  echo "::error::mpicc not found on PATH (even after sourcing /container/config_env.sh)."
  exit 1
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "${WORKDIR}"' EXIT

echo "=== Downloading Scotch ${SCOTCH_VERSION} source ==="
ARCHIVE="${WORKDIR}/scotch-v${SCOTCH_VERSION}.tar.gz"
curl -sL --retry 5 --retry-delay 5 \
  "https://gitlab.inria.fr/scotch/scotch/-/archive/v${SCOTCH_VERSION}/scotch-v${SCOTCH_VERSION}.tar.gz" \
  -o "${ARCHIVE}"
tar -xzf "${ARCHIVE}" -C "${WORKDIR}"

SRC_DIR="${WORKDIR}/scotch-v${SCOTCH_VERSION}"
BUILD_DIR="${SRC_DIR}/build"
mkdir -p "${BUILD_DIR}"

echo "=== Configuring PT-SCOTCH (static, MPI enabled) ==="
cmake -S "${SRC_DIR}" -B "${BUILD_DIR}" \
  -DCMAKE_C_COMPILER="$(command -v mpicc)" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="${SCOTCH_PREFIX}" \
  -DCMAKE_INSTALL_LIBDIR=lib64 \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_PTSCOTCH=ON

echo "=== Building PT-SCOTCH ==="
cmake --build "${BUILD_DIR}" --parallel "$(nproc)"

echo "=== Installing PT-SCOTCH to ${SCOTCH_PREFIX} ==="
cmake --install "${BUILD_DIR}"

if [ ! -f "${SCOTCH_PREFIX}/include/ptscotch.h" ] || [ ! -f "${SCOTCH_PREFIX}/lib64/libptscotch.a" ]; then
  echo "::error::PT-SCOTCH install at ${SCOTCH_PREFIX} is missing expected headers/libs."
  find "${SCOTCH_PREFIX}" -maxdepth 3
  exit 1
fi

echo "=== PT-SCOTCH ${SCOTCH_VERSION} installed at ${SCOTCH_PREFIX} ==="
