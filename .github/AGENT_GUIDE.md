# MPAS-Model CI — Agent Reference Guide

## What is MPAS?

MPAS (Model for Prediction Across Scales) is a community atmospheric model used for weather forecasting and climate research. Scientific validity is non-negotiable — every CI change must preserve the correctness of model results and not hide failures.

MPAS has consistent coding conventions maintained over many years. Follow existing style.

## Repository Layout

This is `NCAR/MPAS-Model-CI`, a fork of `MPAS-Dev/MPAS-Model`. The MPAS source code (Fortran, `src/`, `Makefile`) is inherited from upstream. CI infrastructure lives in `.github/`.

```
.github/
├── ci-config.env                # Central CI configuration (containers, flags, mappings)
├── copilot-instructions.md      # MPAS Fortran coding standards for AI assistants
├── actions/
│   ├── build-mpas/              # Compiles MPAS-A for a given compiler
│   ├── checkout-mpas-source/    # Cross-repo checkout with CI overlay
│   ├── download-testdata/       # Downloads + caches test case archives
│   ├── resolve-container/       # Resolves container image from ci-config.env
│   ├── run-mpas/                # Configures and runs MPAS-A
│   ├── run-perturb-mpas/        # Runs perturbed ensemble members for ECT
│   │   ├── perturb_theta.py     # IC perturbation (theta field)
│   │   └── trim_history.py      # Trims history files for artifact upload
│   ├── validate-ect/            # PyCECT validation
│   ├── ect-summary/             # Consolidated ECT results table
│   └── validate-logs/           # Log comparison (legacy, kept for debugging)
├── test-cases/
│   ├── 240km/config.env         # Standard test case (coverage workflow)
│   ├── 120km/config.env         # Higher-resolution test case
│   └── ect-120km/               # ECT-specific config
│       ├── config.env
│       ├── ect_excluded_vars.txt
│       └── ect_pycect_exclude.json
└── workflows/
    ├── _test-compiler.yml       # Reusable: CPU build + ECT validation
    ├── _test-gpu.yml            # Reusable: GPU build + ECT validation (CIRRUS)
    ├── test-gcc-mpich.yml       # Caller: GNU+MPICH (auto on push/PR)
    ├── test-gcc-openmpi.yml     # Caller: GNU+OpenMPI (dispatch-only)
    ├── test-intel-mpich.yml     # Caller: Intel+MPICH (auto on push/PR)
    ├── test-intel-openmpi.yml   # Caller: Intel+OpenMPI (dispatch-only)
    ├── test-nvhpc-mpich.yml     # Caller: NVHPC+MPICH (auto on push/PR)
    ├── test-nvhpc-openmpi.yml   # Caller: NVHPC+OpenMPI (dispatch-only)
    ├── test-gpu-mpich.yml       # Caller: NVHPC+MPICH GPU (dispatch-only)
    ├── test-gpu-openmpi.yml     # Caller: NVHPC+OpenMPI GPU (dispatch-only)
    ├── ect-test.yml             # Standalone ECT (debugging)
    ├── ect-ensemble-gen.yml     # Generate ensemble summary (manual, expensive)
    ├── coverage.yml             # GCC coverage + Codecov upload
    └── unit-tests.yml           # pFUnit unit tests

tests/                           # pFUnit test infrastructure (repo root)
├── CMakeLists.txt
└── unit/
    ├── CMakeLists.txt
    └── test_spline_interpolation.pf
```

External: `NCAR/mpas-ci-data` — public repo (Git LFS) hosting test case archives, ECT ensemble summary files, and spin-up restart files.

## Branch Structure

- **`master`** — default branch, mirrors upstream MPAS-Model. Workflow files must exist here for the `workflow_dispatch` UI button to appear.
- **`develop`** — upstream develop branch.
- **`feature-ci-cleanup`** — active development branch for CI improvements. PR #18 targets master.

## Workflow Architecture

### Subset Workflows (primary CI)

Each compiler+MPI combination has a thin caller workflow that invokes a reusable template:

- **CPU subsets** call `_test-compiler.yml` with `compiler` and `mpi` inputs
- **GPU subsets** call `_test-gpu.yml` with `mpi` input (always NVHPC)

**MPICH callers** (`test-gcc-mpich`, `test-intel-mpich`, `test-nvhpc-mpich`) run on push/PR to `master`/`develop`.
**OpenMPI and GPU callers** are `workflow_dispatch` only.

### _test-compiler.yml — Reusable CPU Workflow

**Job flow**: `config` → `build` → `ect-run` (3 parallel members) → `ect-validate` → `cleanup`

- Builds in double precision with SMIOL I/O
- Runs 3 perturbed ensemble members in parallel (matrix strategy), each with 4 MPI ranks
- Validates with PyCECT against the ensemble summary file
- If build fails, ECT jobs skip (explicit `needs.build.result == 'success'` check)

### _test-gpu.yml — Reusable GPU Workflow

Same structure as `_test-compiler.yml` but builds with OpenACC (`openacc: 'true'`) and runs on `CIRRUS-4x8-gpu` self-hosted runners.

### Other Workflows

- **ect-test.yml** — standalone 3-member ECT (gcc/openmpi). Kept for debugging.
- **ect-ensemble-gen.yml** — generates the PyCECT ensemble summary file (~200 model runs). Manual trigger only.
- **coverage.yml** — GCC build with `--coverage`, 240km test case, Codecov upload. Runs on push to master.
- **unit-tests.yml** — pFUnit tests across GCC 12/13/14 matrix.

## Configuration: ci-config.env

All container images, compiler mappings, and MPI flags are centralized in `.github/ci-config.env`. Workflows source this file via the `resolve-container` composite action.

Key settings:
- `CONTAINER_IMAGE` / `CONTAINER_IMAGE_GPU` — image templates with `{compiler}` and `{mpi}` placeholders
- `CONTAINER_IMAGE_{compiler}` — per-compiler overrides (Intel pinned to `hpcdev 25.09`)
- `CONTAINER_COMPILER_{name}` — name mappings when image tags differ (e.g., `gcc` → `gcc14`)
- `MAKE_TARGET_{compiler}` — maps CI names to Makefile targets
- `NVHPC_EXTRA_MAKE_FLAGS` / `ONEAPI_EXTRA_MAKE_FLAGS` — compiler-specific build workarounds
- `OPENMPI_RUN_FLAGS` / `MPICH_RUN_ENV_*` — MPI runtime settings

## Container Environment

All builds and runs use `ncarcisl/hpcdev-x86_64` Docker containers. Image names are resolved from `ci-config.env` templates.

Current containers:
- **GCC, NVHPC**: `hpcdev-x86_64:almalinux9-{compiler}-{mpi}-26.02`
- **Intel**: `hpcdev-x86_64:leap-oneapi-{mpi}-25.09` (pinned to avoid IFX 2025.3 fpp regression)
- **GPU**: `hpcdev-x86_64:almalinux9-nvhpc-{mpi}-cuda-26.02`

Container facts:
- `/container/config_env.sh` must be sourced before building or running MPI executables
- Miniforge is installed but the base env is not activated by default — use `eval "$(conda shell.bash hook)" && conda activate base` if needed
- `python3` may resolve to system Python (old) or miniforge Python depending on env activation
- `run-perturb-mpas` handles Python deps with: check import → pip → conda fallback
- Some containers (Leap) lack `cpp`; `build-mpas` installs it if missing

## Composite Actions

### build-mpas
Compiles MPAS-A. Sources `ci-config.env` for make target and workaround flags. Installs `cpp` if missing. For NVHPC, patches `-tp=px` for portable binaries.

### resolve-container
Resolves a container image name from `ci-config.env` templates. Accepts `compiler`, `mpi`, and optional `gpu` inputs. Checks for per-compiler overrides before falling back to the default template.

### checkout-mpas-source
Handles cross-repo checkout: checks out MPAS source, then overlays `.github/` from MPAS-Model-CI if testing an external repo.

### run-perturb-mpas
Runs perturbed ensemble members for ECT. Activates conda, installs netCDF4/numpy, then loops through members applying theta perturbation, running the model, and trimming history files. Supports restart mode.

### validate-ect
Runs PyCECT against an ensemble summary file. Installs dependencies, clones PyCECT, downloads the summary, runs validation, writes enriched result file with dimension metadata.

## Ensemble Consistency Test (ECT)

ECT validates that code changes do not alter model output beyond internal variability. It does **not** require bit-for-bit reproducibility. Reference: Price-Broncucia et al. (2025), doi:10.5194/gmd-18-2349-2025.

Key constraints:
- **Perturbation magnitude**: O(1e-14) for theta, requires double precision
- **Spin-up restart**: cold-start `init.nc` has zero hydrometeors. Ensemble generation runs 24h unperturbed first, then perturbs from the restart.
- **PyCECT minimum members**: ensemble size must be >= number of output variables (~48). Default: 200.
- **Time slice**: always extract last slice (`--tslice -1`) — slice 0 in cold-start mode is the unintegrated initial state.
- Config in `.github/test-cases/ect-120km/config.env`

## Shell Scripting Notes

GitHub Actions runs bash with `set -e -o pipefail`:

- **SIGPIPE**: `tar tzf file.tar.gz | head -1` kills tar (exit 141). Append `|| true`.
- **mpirun exit codes**: gfortran may exit non-zero on IEEE warnings. Use `set +e`/`set -e` and check for output files.
- **OpenMPI in containers**: requires `--allow-run-as-root --oversubscribe` (configured in `ci-config.env`).
- **curl retries**: always use `--retry 5 --retry-delay 5` for large downloads.

## Cross-Repo Testing

Workflows accept `mpas-repository` and `mpas-ref` inputs for testing upstream MPAS-Dev commits. The `checkout-mpas-source` action handles the two-step checkout and CI overlay. See `.github/docs/testing-upstream-commits.md`.

## Security

- **Self-hosted runners**: GPU workflows use `workflow_dispatch` only. Never add `pull_request` triggers — fork PRs could execute arbitrary code on CIRRUS hardware.
- **Secret isolation**: `MPAS_CI_DATA_TOKEN` is only available in jobs that don't check out or execute external code.
- **Cross-repo execution**: `workflow_dispatch` with external repo inputs runs `make` from that repo. Acceptable since only write-access users can trigger it.

## Known Issues

- **IFX 2025.3 fpp regression**: breaks `#define COMMA ,` pattern in 6+ framework files. Intel pinned to hpcdev 25.09 (IFX 2025.2.1). Remove override when IFX 2025.4+ is available.
- **NVHPC+OpenMPI**: model exits 134 (SIGABRT) on GA runners with 4 ranks. MPICH works. Low priority (dispatch-only).
- **NVHPC/Intel MPI F08 bindings**: broken with hpcdev MPI libraries. Both use `MPAS_MPI_F08=0` workaround.
