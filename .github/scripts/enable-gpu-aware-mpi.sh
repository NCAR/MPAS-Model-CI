#!/bin/bash
# Set config_gpu_aware_mpi = .true. in the &development group of a namelist.atmosphere
# (creating the group if it is missing). MPAS host-stages halo exchanges itself unless this is set,
# so the MPI library's GPU support (see gpu-aware-mpi-env.sh) has nothing to do without it.
# usage: enable-gpu-aware-mpi.sh <path/to/namelist.atmosphere>
set -e
NML="${1:?usage: enable-gpu-aware-mpi.sh <namelist.atmosphere>}"
python3 - "${NML}" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
text = p.read_text()
if re.search(r"^\s*&development\b", text, flags=re.MULTILINE):
    def edit(m):
        block = m.group(0)
        if re.search(r"config_gpu_aware_mpi\s*=", block):
            return re.sub(r"config_gpu_aware_mpi\s*=\s*\.\w+\.", "config_gpu_aware_mpi = .true.", block)
        return re.sub(r"(\n\s*/\s*)$", r"\n    config_gpu_aware_mpi = .true.\1", block, count=1)
    text = re.sub(r"^\s*&development\b[\s\S]*?\n\s*/\s*", edit, text, count=1, flags=re.MULTILINE)
else:
    text = text.rstrip() + "\n&development\n    config_gpu_aware_mpi = .true.\n/\n"
p.write_text(text)
PY
echo "GPU-aware MPI enabled in ${NML}; &development now reads:"
awk '/^[[:space:]]*&development/,/^[[:space:]]*\//' "${NML}"
