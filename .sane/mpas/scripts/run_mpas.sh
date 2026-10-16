#!/bin/bash
# Run an MPAS-Atmosphere test case in its own directory.
help()
{
  echo "./run_mpas.sh -e <atmosphere_model> -c <case dir> -r <run dir> -n <ranks> [-t <run_duration D_HH:MM:SS>]"
}

while getopts e:c:r:n:t:h opt; do
  case $opt in
    e) exe="$OPTARG" ;;
    c) casedir="$OPTARG" ;;
    r) rundir="$OPTARG" ;;
    n) ranks="$OPTARG" ;;
    t) duration="$OPTARG" ;;
    h) help; exit 0 ;;
    *) help; exit 1 ;;
  esac
done
if [ -z "$exe" ] || [ -z "$casedir" ] || [ -z "$rundir" ] || [ -z "$ranks" ]; then help; exit 1; fi
[ -x "$exe" ] || { echo "Executable '$exe' not found"; exit 1; }

rm -rf "$rundir"; mkdir -p "$rundir"
exe=$(realpath "$exe")
# Large/immutable inputs are linked; namelist/streams are copied since they get edited
for f in "$casedir"/*; do
  case "$(basename "$f")" in
    namelist.atmosphere|streams.atmosphere) cp "$f" "$rundir/" ;;
    *) ln -sf "$(realpath "$f")" "$rundir/" ;;
  esac
done
ln -sf "$exe" "$rundir/atmosphere_model"
cd "$rundir" || exit 1

part=$(ls x1.*.graph.info.part.${ranks} 2>/dev/null | head -1)
if [ -z "$part" ]; then
  echo "No partition file for $ranks ranks in $casedir (available:)"
  ls x1.*.graph.info.part.* 2>/dev/null
  exit 1
fi
[ -n "$duration" ] && sed -i "s/config_run_duration = '[^']*'/config_run_duration = '${duration}'/" namelist.atmosphere
grep config_run_duration namelist.atmosphere

mpiexec -n "$ranks" ./atmosphere_model
rc=$?

# MPAS can exit 0 after logging errors, so also check the log and the output
if [ $rc -ne 0 ]; then echo "atmosphere_model exited with $rc"; exit $rc; fi
if grep -q "CRITICAL ERROR" log.atmosphere.0000.out 2>/dev/null; then
  echo "CRITICAL ERROR found in log.atmosphere.0000.out"; exit 1
fi
ls history.*.nc > /dev/null 2>&1 || { echo "No history file written"; exit 1; }
