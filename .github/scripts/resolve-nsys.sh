#!/usr/bin/env bash
# Pick a working `nsys` binary. NVHPC may put a stub first on PATH that fails with
# "nsys-Error-Version ... Nsight_Systems/bin is not available in this installation";
# we prefer /opt/nvidia/nsight-systems or CUDA toolkit paths and test with `nsys --version`.
#
# Usage: source this file from bash, then call resolve_nsys.
# On success: exports NSYS_BIN to the chosen executable.
# shellcheck shell=bash

resolve_nsys() {
  if [ -n "${NSYS_BIN:-}" ] && [ -x "${NSYS_BIN}" ] && "${NSYS_BIN}" --version &>/dev/null; then
    export NSYS_BIN
    return 0
  fi

  local prepend="" d dir
  local -a dirs

  shopt -s nullglob
  for d in /opt/nvidia/nsight-systems/*/bin /usr/local/cuda/bin /usr/local/cuda-*/bin; do
    [ -d "$d" ] && prepend="${prepend}${d}:"
  done
  shopt -u nullglob

  export PATH="${prepend}${PATH}"

  IFS=':' read -ra dirs <<< "${PATH}"
  for dir in "${dirs[@]}"; do
    [ -z "$dir" ] && continue
    [ -x "${dir}/nsys" ] || continue
    if "${dir}/nsys" --version &>/dev/null; then
      NSYS_BIN="${dir}/nsys"
      export NSYS_BIN
      return 0
    fi
  done

  # Explicit paths (some images omit standard entries from PATH)
  local c
  shopt -s nullglob
  for c in /opt/nvidia/nsight-systems/*/bin/nsys /usr/local/cuda/bin/nsys /usr/local/cuda-*/bin/nsys; do
    [ -x "$c" ] || continue
    if "$c" --version &>/dev/null; then
      NSYS_BIN="$c"
      export NSYS_BIN
      shopt -u nullglob
      return 0
    fi
  done
  shopt -u nullglob
  return 1
}
