#!/bin/bash
# Compare the first history file of a reference run dir against one or more test run dirs.
# cmp first (instant); fall back to the data-level NetCDF comparison used by the GitHub CI.
help() { echo "./compare_bfb.sh -c <compare-bfb-nc.py> -p <python> <ref run dir> <test run dir> [...]"; }
while getopts c:p:h opt; do
  case $opt in
    c) compare_py="$OPTARG" ;;
    p) python="$OPTARG" ;;
    h) help; exit 0 ;;
    *) help; exit 1 ;;
  esac
done
shift $((OPTIND - 1))
ref_dir=$1; shift
[ -n "$ref_dir" ] && [ $# -gt 0 ] || { help; exit 1; }

ref=$(ls "$ref_dir"/history.*.nc 2>/dev/null | head -1)
[ -n "$ref" ] || { echo "No reference history file in $ref_dir"; exit 1; }

fail=0
for dir in "$@"; do
  test_file=$(ls "$dir"/history.*.nc 2>/dev/null | head -1)
  if [ -z "$test_file" ]; then echo "$dir: history file missing"; fail=1; continue; fi
  if cmp -s "$ref" "$test_file"; then echo "$dir: byte-identical"; continue; fi
  out=$("$python" "$compare_py" "$ref" "$test_file"); rc=$?
  if [ $rc -eq 0 ]; then echo "$dir: data-identical ($out)"; else echo "$dir: DIFFER - $out"; fail=1; fi
done
exit $fail
