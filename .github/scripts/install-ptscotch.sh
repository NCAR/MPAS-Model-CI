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
