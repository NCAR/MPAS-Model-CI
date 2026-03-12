# MPAS-Model CI — Agent Reference Guide

## What is MPAS?

MPAS (Model for Prediction Across Scales) is a community atmospheric model used for weather forecasting. Its outputs inform decisions that protect lives and property. Scientific validity is non-negotiable — every CI change must preserve the correctness of model results and not hide failures.

MPAS has been maintained with consistent coding conventions and project structure over many years. Follow the style of existing code. Do not introduce patterns, naming conventions, or organizational choices that diverge from what is already in the repository.

## Purpose of CI

The CI exists to support code health for a community model. Scientists and students — not just software engineers — need to understand and use these workflows. Keep configurations readable, well-commented, and avoid unnecessary abstraction.

## Repository Layout

This is `NCAR/MPAS-Model-CI`, a fork of `MPAS-Dev/MPAS-Model`. The MPAS source code (Fortran, `src/`, `Makefile`) is inherited from upstream. The CI infrastructure is added on top in `.github/`.

```
.github/
├── actions/                  # Reusable composite actions
│   ├── build-mpas/           # Compiles MPAS-A for a given compiler
│   ├── download-testdata/    # Downloads + caches test case archives
│   ├── run-mpas/             # Configures and runs MPAS-A
│   ├── run-perturb-mpas/     # Runs perturbed ensemble members for ECT
│   │   ├── perturb_theta.py  # IC perturbation (theta field)
│   │   └── trim_history.py   # Trims history files for artifact upload
│   ├── validate-ect/         # PyCECT validation (shared by all ECT workflows)
│   ├── ect-summary/          # Consolidated ECT results table generator
│   └── validate-logs/        # Compares run logs against reference output
│       └── compare_logs.py   # Log comparison logic
├── contributors-sync/
│   ├── generate_ci_docs.py    # Generates ci-cd.md for contributor's guide
│   ├── sync-docs.yml          # Workflow template for NCAR/contributors-MPAS-A
│   └── README.md              # Deployment docs for the sync tooling
├── docs/
│   └── testing-upstream-commits.md  # How to test MPAS-Dev/MPAS-Model commits
├── linting/
│   └── fortitude_config.toml  # Fortitude linting rules and exclusions
├── test-cases/
│   ├── 240km/config.env      # Standard test case (6h run, ~20min)
│   ├── 120km/config.env      # Higher-resolution test case (2h run)
│   └── ect-120km/            # ECT-specific config
│       ├── config.env         # 24h spinup + 6h perturbed runs
│       ├── ect_excluded_vars.txt  # Variables excluded from PyCECT
│       └── ect_pycect_exclude.json
└── workflows/
    ├── test-ga-nogpu.yml      # Full matrix build/run/validate + ECT
    ├── test-cirrus-nvhpc.yml  # NVHPC GPU/NoGPU on CIRRUS runners + ECT
    ├── ect-test.yml           # Standalone ECT (3 members, gcc/openmpi)
    ├── ect-ensemble-gen.yml   # Generate 200-member ensemble summary
    ├── coverage.yml           # GCC coverage + Codecov upload
    ├── fortran-linting.yml    # Fortitude Fortran source linting
    └── unit-tests.yml         # pFUnit unit tests (standalone procedures)

tests/                         # pFUnit test infrastructure (repo root)
├── CMakeLists.txt             # Builds mpas_testable_procedures library
└── unit/
    ├── CMakeLists.txt         # pFUnit CTest targets
    └── test_spline_interpolation.pf  # Starter tests (8 tests)
```

External: `NCAR/mpas-ci-data` — public repo (Git LFS) hosting test case archives (`240km.tar.gz`, `120km.tar.gz`), ECT ensemble summary files, and spin-up restart files.

## Branch Structure

- **`master`** — default branch, mirrors upstream MPAS-Model. Workflow files must exist here for the workflow_dispatch UI button to appear.
- **`develop`** — upstream develop branch.
- **`feature-ci-test-cases`** — **active development branch** for CI. Contains all current work (79 commits ahead of master). This is where new CI features should be developed and tested.
- **`feature-ci`** — older CI branch, largely superseded by `feature-ci-test-cases`.
- **`feature-ci-hpcdev-containers`** — experimental branch testing `ncarcisl/hpcdev-x86_64` containers with `gcc14` only. Created from `feature-ci-test-cases` with different container naming conventions. Not actively used.

## Workflow Overview

### test-ga-nogpu.yml — Full Matrix Testing

The main CI workflow. Builds every compiler/MPI/IO combination, runs 240km test case at 1 and 4 MPI ranks, validates logs against reference, and runs ECT on the 120km test case.

**Matrix**: `compiler: [gcc, nvhpc, oneapi]` × `mpi: [mpich3, mpich, openmpi]` × `io: [smiol, pio]` × `num-procs: [1, 4]`

**Job flow**: `build` → `run` → `validate` (log comparison + decomposition test)
                      → `ect-run` → `ect-validate` → `ect-summary`
                      → `cleanup`

**Container pattern**: `ncarcisl/cisldev-x86_64-almalinux9-{compiler}-{mpi}:devel`

### test-cirrus-nvhpc.yml — NVHPC GPU Testing

Runs on self-hosted CIRRUS runners with GPU access. NVHPC only, tests both `nogpu` and `cuda` GPU modes. Includes embedded ECT.

**Matrix**: `mpi: [mpich3, mpich, openmpi]` × `gpu: [nogpu, cuda]` × `io: [smiol, pio]`

**Runner**: `group: CIRRUS-4x8-gpu` (self-hosted), `max-parallel: 2`

**Container pattern**: `ncarcisl/cisldev-x86_64-almalinux9-nvhpc-{mpi}[-cuda]:devel`

### ect-test.yml — Standalone ECT

Quick 3-member ECT validation using gcc/openmpi. Triggered on push to master or manually. Lighter weight than the full matrix ECT in test-ga-nogpu.

### ect-ensemble-gen.yml — Ensemble Generation

Expensive workflow (~200 model runs). Generates the PyCECT ensemble summary file used by all ECT validation. Only run manually when science changes require a new reference ensemble.

**Job flow**: `prepare` (compute batch ranges) → `build` → `spinup` (24h unperturbed) → `run-ensemble` (batched) → `generate-summary` (pyEnsSumMPAS) → `cleanup`

### coverage.yml — Code Coverage

Single-job workflow: builds with GCC coverage flags (`-O0 --coverage`), runs 240km test case at 1 rank, generates lcov report, uploads to Codecov.

### fortran-linting.yml — Fortran Source Linting

Runs `fortitude-lint` on all Fortran source under `src/` (excluding `src/external/` and WRF physics). Triggered on PRs and pushes touching `src/` or linting config. Non-blocking (`--exit-zero`) to establish a baseline — results are uploaded as artifacts. Config lives in `.github/linting/fortitude_config.toml` (all rules enabled, 132-char line limit, single quotes enforced). Adapted from the CAM-SIMA MPAS dynamical core CI.

### unit-tests.yml — pFUnit Unit Tests

Builds and runs pFUnit-based unit tests for standalone MPAS procedures that don't require the full framework. Tests live in `tests/` at the repo root. Currently tests `mpas_spline_interpolation.F` (8 tests covering linear interpolation, cubic splines, and spline integration). Runs across GCC 12/13/14 matrix. pFUnit is cached between runs.

The `tests/CMakeLists.txt` builds a `mpas_testable_procedures` library from `mpas_kind_types.F` and `mpas_spline_interpolation.F`, compiled with `-cpp -ffree-form` (MPAS uses `.F` extension for free-form Fortran, but gfortran treats `.F` as fixed-form by default). To add more testable source files, add them to this library and create new `.pf` test files in `tests/unit/`. Best candidates for expansion: `mpas_geometry_utils.F`, `mpas_sort.F`.

## Composite Actions

### build-mpas

Compiles MPAS-A for a given compiler family. Maps input names (`gcc`, `nvhpc`, `oneapi`) to make targets (`gfortran`, `nvhpc`, `intel`). Sources `/container/config_env.sh` for library paths. For NVHPC:
- Prepends `-tp=px` to flags for portable x86-64 binaries (CI build and run happen on different runners)
- Passes `MPAS_MPI_F08=0` to make to disable MPI F08 bindings, working around a known incompatibility between MPICH4's F08 bindings and NVHPC's broken CFI implementation (pre-2024 versions). Without this, MPICH4 builds crash at runtime with `CFI_is_contiguous: unsupported array rank`. See [pmodels/mpich#6505](https://github.com/pmodels/mpich/issues/6505). This can be removed when the container upgrades to NVHPC 24.x+.

### download-testdata

Downloads and extracts a test case archive from `NCAR/mpas-ci-data`. Uses `actions/cache@v4` to cache the archive (key: `testdata-v1-{archive}`), falling back to `curl` download with retry logic (`--retry 5 --retry-delay 5`). Reads `RESOLUTION` and `DATA_REPO` from the test case's `config.env`.

### run-mpas

Configures namelist/streams and runs MPAS-A. Calls `download-testdata` internally. Key details:
- `mpi-impl: 'openmpi'` adds `--allow-run-as-root --oversubscribe` flags (does NOT auto-detect)
- `mpi-impl: 'mpich'` sets `MPICH_GPU_SUPPORT_ENABLED=0` to prevent yaksa CUDA stub crashes
- `strict-exit-check: 'false'` tolerates non-zero exit codes (gfortran IEEE warnings)
- **Variable clobbering**: sourcing `config.env` overwrites `RESOLUTION` — the action saves and restores the input value

### run-perturb-mpas

Runs perturbed MPAS-A ensemble members for ECT. Contains `perturb_theta.py` (applies O(1e-14) multiplicative perturbation to theta field) and `trim_history.py` (extracts single time slice, removes excluded variables). Supports batched runs via `member-start`/`member-end` inputs. `trim_history.py` defaults to `--tslice -1` (last time slice) and supports negative Python-style indexing. The action auto-detects the last time slice from the history file and logs all available slices with timestamps for debugging.

When a `restart-file` is provided:
1. Extracts `xtime` variable to get the timestamp
2. Renames the file to `restart.YYYY-MM-DD_HH.MM.SS.nc` (MPAS format)
3. Creates `restart_timestamp` text file
4. Sets `config_do_restart = .true.` and `config_start_time = 'file'`

### validate-ect

Runs PyCECT against an ensemble summary file to validate history output. Encapsulates all PyCECT-related logic that was previously duplicated across `test-ga-nogpu.yml`, `test-cirrus-nvhpc.yml`, and `ect-test.yml`.

Key inputs:
- `history-dir` — path to directory containing history `.nc` files
- `label` — human-readable label for log annotations (e.g., `gcc/mpich3/smiol/4proc`)
- `dimensions` — multi-line `key=value` pairs written into the result file for the summary action

The action:
1. Installs PyCECT dependencies (`numpy<2`, `scipy`, `netCDF4`)
2. Clones PyCECT at the tag specified by `PYCECT_TAG` in `config.env`
3. Downloads the ensemble summary file from `NCAR/mpas-ci-data`
4. Runs `pyCECT.py` and parses the PASSED/FAILED result
5. Writes an enriched `ect-result.txt` with the result and dimension metadata

Outputs: `result` (PASSED/FAILED/SKIPPED/ERROR) and `available` (whether summary file was found).

### ect-summary

Generates a consolidated ECT results table from enriched result files produced by `validate-ect`. Auto-discovers column names from the key=value pairs in each result file, builds a Markdown table, and writes it to `$GITHUB_STEP_SUMMARY`.

Input: `results-path` — directory containing downloaded `ect-result-*` artifact subdirectories.

Both `test-ga-nogpu.yml` and `test-cirrus-nvhpc.yml` use the same action; column discovery is automatic based on whatever dimensions the `validate-ect` action wrote.

### validate-logs

Compares run logs against reference output using `compare_logs.py`. Supports:
- Reference log comparison (1-proc logs against `.github/test-cases/240km/reference_log.atmosphere.0000.out`)
- Decomposition test (4-proc vs 1-proc log comparison)
- `--allow-missing` flag to tolerate missing configs (when some matrix combos fail to build/run)

## Container Environment

All builds and runs use NCAR Docker containers: `docker.io/ncarcisl/cisldev-x86_64-almalinux9-{compiler}-{mpi}:devel`

Key facts:
- **Full registry path required**: All container `image:` references must use `docker.io/ncarcisl/...`, not bare `ncarcisl/...`. The CIRRUS Kubernetes cluster requires fully-qualified image paths after a 2026 infrastructure upgrade.
- `python` is not on PATH; always use `python3`
- `pip` is not on PATH; use `python3 -m ensurepip --upgrade 2>/dev/null || true` then `python3 -m pip install ...`
- `/container/config_env.sh` must be sourced before running MPI executables or building
- `free` may not be available in all containers

There is also an alternative container set `ncarcisl/hpcdev-x86_64` with tags like `almalinux9-gcc14-{mpi}-26.02` (tested on `feature-ci-hpcdev-containers` branch). These use a more generic prefix and pinned version tags instead of `:devel`.

### MPI Matrix Values

The workflow matrix uses three MPI values:
- `mpich3` — MPICH 3.x
- `mpich` — MPICH 4.x (the container `cisldev-...-mpich:devel` ships MPICH 4)
- `openmpi` — OpenMPI

The `mpi-impl` mapping in workflows uses `matrix.mpi != 'openmpi' && 'mpich' || 'openmpi'` — both `mpich3` and `mpich` map to the generic `mpich` MPI implementation (same flags, same `MPICH_GPU_SUPPORT_ENABLED=0`). Only `openmpi` gets the `--allow-run-as-root --oversubscribe` flags.

## MPI Compatibility Matrix (4-rank, 240km, GitHub Actions runners)

| Compiler | MPI | 1-proc | 4-proc | Notes |
|----------|-----|--------|--------|-------|
| gcc | openmpi | pass | pass | Needs `--allow-run-as-root --oversubscribe` |
| gcc | mpich3 | pass | **fail** | Heap corruption during mesh bootstrap |
| gcc | mpich | pass | **fail** | Same heap corruption as mpich3 |
| nvhpc | openmpi | pass | **fail** | malloc assertion in nvhpc Fortran runtime |
| nvhpc | mpich3 | pass | pass | |
| nvhpc | mpich | pass | **fail** | Requires `MPAS_MPI_F08=0` (CFI bug); 4-proc failure is container issue |
| oneapi | openmpi | pass | pass | Needs `--allow-run-as-root --oversubscribe` |
| oneapi | mpich3 | pass | pass | |
| oneapi | mpich | untested | untested | |

The gcc/mpich and nvhpc/openmpi 4-proc failures are container library issues, not MPAS bugs. They crash with glibc heap corruption during SMIOL parallel I/O initialization. The nvhpc/mpich 1-proc runs now pass with the `MPAS_MPI_F08=0` workaround; 4-proc failures remain a container issue.

**ECT ensemble generation uses gcc/openmpi** because it works at both 1 and 4 ranks with gfortran.

## Shell Scripting in GitHub Actions

GitHub Actions runs bash with `set -e -o pipefail`. This causes subtle failures:

- **SIGPIPE**: `tar tzf file.tar.gz | head -1` kills tar with SIGPIPE (exit 141). Always append `|| true` and add a fallback:
  ```bash
  CASE_DIR=$(tar tzf "${ARCHIVE}" 2>/dev/null | head -1 | cut -d/ -f1 || true)
  if [ -z "${CASE_DIR}" ]; then
    CASE_DIR=$(ls -td */ 2>/dev/null | head -1 | tr -d '/')
  fi
  ```

- **mpirun exit codes**: gfortran-compiled MPAS may exit non-zero due to IEEE floating-point warnings, not crashes. Wrap with `set +e` / `set -e` and check for output files as the success indicator:
  ```bash
  set +e
  timeout ${TIMEOUT}m mpirun -n ${NRANKS} ${MPI_FLAGS} ./atmosphere_model
  RUN_STATUS=$?
  set -e
  HIST_FILE=$(ls -t history.*.nc 2>/dev/null | head -1 || true)
  ```

- **OpenMPI in containers**: Always pass `--allow-run-as-root --oversubscribe` when running OpenMPI inside Docker containers on GitHub Actions runners. The `run-mpas` action requires `mpi-impl: 'openmpi'` to set these flags — it does **not** auto-detect. The `run-perturb-mpas` action defaults to `mpi-impl: 'openmpi'`.

- **curl failures**: Large file downloads from GitHub can fail with `exit code 18` (transfer closed). Always use `--retry 5 --retry-delay 5`. The `download-testdata` action handles this, but direct `curl` calls in workflows (e.g., downloading spin-up restart files) need these flags explicitly.

## Ensemble Consistency Test (ECT)

ECT validates that code changes do not alter model output beyond internal variability. It does not require bit-for-bit reproducibility — scientifically equivalent changes pass. Reference: Price-Broncucia et al. (2025), doi:10.5194/gmd-18-2349-2025.

ECT workflows:
- `ect-ensemble-gen.yml` — Generates N perturbed runs and produces a PyCECT summary file (expensive, manual trigger)
- `ect-test.yml` — Standalone: runs 3 members against an existing summary file (fast, used for validation)
- `test-ga-nogpu.yml` — Embedded ECT: runs 3 perturbed members for every compiler/MPI/IO/num-procs combination alongside the existing 240km log-based validation
- `test-cirrus-nvhpc.yml` — Embedded ECT: runs 3 perturbed members for every MPI/GPU/IO combination alongside existing log validation

The embedded ECT jobs use the gcc-generated ensemble summary for all compiler/MPI/decomposition comparisons. Per the paper's authors, only one compiler is needed for ensemble generation — the summary should still detect meaningful changes across other compilers, MPI libraries, and decompositions.

### ECT Job Structure in Build/Run Workflows

ECT runs are batched: all 3 ensemble members run sequentially in a single job per matrix combination (not 3 separate jobs). This reduces redundant container startups and test case downloads.

Each `ect-validate` job invokes the `validate-ect` composite action, which installs PyCECT, downloads the summary file, runs validation, and writes an enriched `ect-result.txt` with key=value dimension metadata. The result artifact is uploaded for the summary job. A final `ect-summary` job uses the `ect-summary` composite action, which downloads all result artifacts and generates a consolidated Markdown table in `$GITHUB_STEP_SUMMARY`.

The validate-ect action replaced ~80 lines of duplicated inline logic across three workflows. The ect-summary action replaced ~40 lines duplicated across two workflows.

### ECT Key Constraints

- **24-hour spin-up**: Hydrometeor fields are zero in cold-start `init.nc`. The ensemble generation workflow runs a 24h unperturbed simulation (4 MPI ranks, `strict-exit-check: 'false'`) first, then uses the restart file as the starting point for all perturbed members. The restart file is both **cached** (`actions/cache/save@v4`, key `ect-spinup-restart-{sha}`) and **pushed to `NCAR/mpas-ci-data`** immediately after the spinup job completes — before ensemble members run. This ensures the restart persists even if later jobs fail. Consumer workflows (`ect-test.yml`, `test-cirrus-nvhpc.yml`) try cache restore first, then fall back to downloading from `mpas-ci-data` via curl. **MPAS restart requirements**: restart mode needs (1) a file named `restart.YYYY-MM-DD_HH.MM.SS.nc` matching the filename template in `streams.atmosphere`, and (2) a `restart_timestamp` text file containing that timestamp. The `run-perturb-mpas` action handles both automatically. See Price-Broncucia et al. (2025), Section 3.2.
- **PyCECT requires ensemble size >= number of output variables** (~47 after trimming for the 120km case; minimum 48). The default of 200 members is recommended. The tool exits 0 even on failure — always verify the output file exists.
- **History time slice selection**: `trim_history.py` always extracts the **last** time slice (`--tslice -1`) from the history file, which is the end-of-run forecast state. This is critical: in cold-start mode (no spin-up restart), MPAS writes the initial state as time slice 0 before any integration — extracting that would show zero variability and PyCECT would fail. The action auto-detects the number of slices and always selects the last one regardless of run mode. Trimmed files also have excluded variables removed (PV diagnostics, integers, edge velocity per `ect_excluded_vars.txt`) to keep artifact sizes manageable.
- **PyCECT `--jsonfile` path pitfall**: `pyEnsSumMPAS.py` writes auto-detected exclusions to `NEW.<jsonfile>`. If `--jsonfile` includes a directory (e.g., `pycect/exclude.json`), it tries to create `NEW.pycect/exclude.json` — a nonexistent directory — and crashes. Always pass a filename in the working directory, not a subdirectory path.
- **ECT perturbation magnitude**: The paper recommends O(1e-14) for theta perturbations, matching CESM convention. This requires a run long enough (6 hours) for perturbations to propagate across all fields. Magnitudes of 1e-1 or larger cause NaN divergence.
- ECT configuration lives in `.github/test-cases/ect-120km/config.env`
- Summary files and the spin-up restart are versioned and uploaded to `NCAR/mpas-ci-data` with metadata (requires `MPAS_CI_DATA_TOKEN` secret with repo scope)
- The `output` stream in `streams.atmosphere` defaults to `output_interval="none"` — ECT workflows must override this via sed to produce history files

## Cross-Repo Testing (Testing Upstream MPAS-Model Commits)

All five CI workflows accept `mpas-repository` and `mpas-ref` workflow_dispatch inputs, allowing users to build and test MPAS source from any public fork (e.g. `MPAS-Dev/MPAS-Model`) using this repo's CI infrastructure. See `.github/docs/testing-upstream-commits.md` for user-facing documentation.

How it works:
- **Build jobs** do a two-step checkout: (1) checkout the target MPAS repo with submodules, (2) overlay `.github/` from MPAS-Model-CI so composite actions (`uses: ./.github/actions/...`) resolve correctly.
- **Run, validate, ECT, and summary jobs** only checkout MPAS-Model-CI (for composite actions and test case configs). They receive the compiled executable via artifacts, so they never need the MPAS source.
- When inputs are empty (the default), behavior is identical to a normal run — the workflow checks out MPAS-Model-CI at the triggered ref.

Build job checkout pattern:
```yaml
- uses: actions/checkout@v4
  with:
    repository: ${{ inputs.mpas-repository || github.repository }}
    ref: ${{ inputs.mpas-ref || '' }}
    submodules: 'true'

- uses: actions/checkout@v4
  if: ${{ inputs.mpas-repository != '' }}
  with:
    path: _ci
    sparse-checkout: .github

- name: Overlay CI infrastructure
  if: ${{ inputs.mpas-repository != '' }}
  shell: bash
  run: cp -r _ci/.github . && rm -rf _ci
```

The `ect-ensemble-gen.yml` `generate-summary` job uses a variant: it checks out `Registry.xml` from the target MPAS repo (for version metadata) and overlays `config.env` from MPAS-Model-CI.

The long-term goal is for these CI workflows to eventually live in `MPAS-Dev/MPAS-Model` itself, but the timeline is uncertain. The cross-repo inputs provide a workable interim solution for demonstrating CI against upstream code.

## Triggering Workflows via CLI

```bash
# Run a workflow on the feature branch against upstream MPAS-Model develop
gh workflow run test-ga-nogpu.yml \
  -R NCAR/MPAS-Model-CI \
  --ref feature-ci-test-cases \
  -f mpas-repository=MPAS-Dev/MPAS-Model \
  -f mpas-ref=develop

# List recent runs
gh run list -R NCAR/MPAS-Model-CI -w "test-ga-nogpu.yml" -L 5

# View a specific run
gh run view <run-id> -R NCAR/MPAS-Model-CI

# Get job details via API
gh api repos/NCAR/MPAS-Model-CI/actions/runs/<run-id>/jobs
```

## workflow_dispatch Visibility

GitHub only shows the workflow_dispatch trigger button for workflows defined on the **default branch** (master). When adding or modifying workflow_dispatch workflows on feature branches, the workflow file must also exist on master for the UI button to appear. Sync workflow files to master when needed.

## Test Data and Caching

Test case archives are hosted in `NCAR/mpas-ci-data` and downloaded via `download-testdata`. The action uses `actions/cache@v4` with key `testdata-v1-{archive}` to cache archives across workflow runs, avoiding repeated large downloads.

Test cases:
- `240km.tar.gz` — standard test case used by `test-ga-nogpu` and `test-cirrus-nvhpc` run jobs
- `120km.tar.gz` — higher-resolution case used by ECT (via `ect-120km` config which maps to this archive)

ECT also downloads:
- `mpas_ect_summary_120km.nc` — ensemble summary file (from `NCAR/mpas-ci-data`)
- `mpas_ect_summary_120km_restart.nc` — spin-up restart file (from `NCAR/mpas-ci-data`)

These are downloaded via direct `curl` in workflow steps (not through `download-testdata`), with `--retry 5 --retry-delay 5`.

## Common Pitfalls

1. **Large files**: Test case archives (>100MB) cannot be stored in the repo. They go in `NCAR/mpas-ci-data` with Git LFS and are downloaded at runtime via curl.
2. **Matrix job dependencies**: `needs: build` with matrix jobs causes all run jobs to skip if any build fails. Use `if: ${{ !cancelled() }}` on the dependent job to allow partial runs.
3. **Artifact patterns**: Use `continue-on-error: true` on artifact download steps and gate subsequent steps with `if: steps.<id>.outcome == 'success'` to handle missing artifacts gracefully.
4. **YAML heredocs**: EOF terminators at column 1 inside run blocks can confuse the YAML parser. Use string concatenation for multi-line commit messages instead.
5. **Registry.xml version extraction**: The file contains both `<?xml version="1.0"?>` and `<registry ... version="8.3.1">`. Use `grep -oP '<registry.*version="\K[^"]+'` to target only the registry version.
6. **config.env variable clobbering**: Sourcing `config.env` sets shell variables like `RESOLUTION=120km`. If a calling script already has a `RESOLUTION` variable (e.g., `ect-120km`), it gets overwritten. Always save variables you need before sourcing, or restore them after.
7. **MPAS restart_timestamp**: When `config_do_restart = .true.`, MPAS reads a `restart_timestamp` text file to determine which restart file to open (matching the `filename_template` in the restart stream). Without this file the model immediately crashes with a Fortran runtime error. The file contains a single line like `2010-10-24_00:00:00`.
8. **Default MPI ranks**: ECT ensemble generation uses 4 MPI ranks (requires `graph.info.part.4` in the test case archive). The 120km archive includes partition files for 4, 36, and 128 ranks.
9. **Ignored files**: Some files under `.github/` may be gitignored. Use `git add -f` to force-add them when needed.
10. **PyCECT numpy compatibility**: PyCECT requires `numpy<2`. Always install with `pip install "numpy<2" scipy netCDF4`.
11. **NVHPC `-tp=native`**: NVHPC defaults to generating code for the build host's CPU. In CI the build and run happen on different runners, so `build-mpas` patches the Makefile to use `-tp=px` (portable x86-64).
12. **NVHPC + MPICH4 CFI crash**: MPICH4's F08 bindings call `CFI_is_contiguous`, which crashes on NVHPC versions before 2024 (`unsupported array rank` with garbage values). The `build-mpas` action forces `MPAS_MPI_F08=0` for all NVHPC builds to use `use mpi` instead of `use mpi_f08`. See [pmodels/mpich#6505](https://github.com/pmodels/mpich/issues/6505).
13. **Container image paths**: All `image:` references in workflow files must use fully-qualified paths (`docker.io/ncarcisl/...`), not bare names (`ncarcisl/...`). The CIRRUS Kubernetes cluster requires this after a 2026 infrastructure upgrade.
14. **MPAS `.F` files are free-form**: MPAS uses `.F` file extensions for free-form Fortran with C preprocessor directives, but gfortran treats `.F` as fixed-form by default. When compiling MPAS source outside the MPAS Makefile (e.g., pFUnit tests), pass `-cpp -ffree-form` (GCC) or `-fpp -free` (Intel).
15. **ECT time slice 0 in cold-start mode**: In cold-start mode (`config_do_restart = .false.`), MPAS writes the initial state as time slice 0 in the history file before any time integration. The end-of-run forecast is slice 1. In restart mode, the initial-time output alarm is reset, so only one slice is written (the forecast). Always use `tslice=-1` (last slice) to get the correct state regardless of mode.

## Development History

The CI was built incrementally on the `feature-ci-test-cases` branch. Key milestones:
1. Basic CI: build/run/validate workflows with 240km test case
2. Multi-rank testing: 1-proc and 4-proc decomposition comparisons
3. ECT integration: standalone `ect-test.yml`, then `ect-ensemble-gen.yml` for summary generation
4. Embedded ECT: added `ect-run`/`ect-validate`/`ect-summary` jobs to both main workflows
5. Optimization: batched ECT members, cached test data, consolidated summary tables
6. Cross-repo testing: `mpas-repository`/`mpas-ref` inputs for testing upstream commits
7. ECT modularity: extracted `validate-ect` and `ect-summary` composite actions from duplicated inline logic
8. Documentation generator: `contributors-sync/generate_ci_docs.py` auto-generates the CI/CD page for the contributor's guide
9. ECT time slice fix: always extract last time slice from history files, fixing cold-start mode analysis
10. Fortran linting: `fortitude-lint` workflow with configurable rules, adapted from CAM-SIMA
11. pFUnit scaffolding: unit test infrastructure with CMake, GCC 12/13/14 matrix, starter spline interpolation tests
12. Container compatibility: fully-qualified `docker.io/` image paths for CIRRUS cluster upgrades
13. Restart caching: spin-up restart pushed to `mpas-ci-data` and cached immediately after generation
14. NVHPC MPICH4 fix: disable MPI F08 bindings (`MPAS_MPI_F08=0`) to work around NVHPC CFI incompatibility
