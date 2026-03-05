# MPAS-Model CI — Agent Reference Guide

## What is MPAS?

MPAS (Model for Prediction Across Scales) is a community atmospheric model used for weather forecasting. Its outputs inform decisions that protect lives and property. Scientific validity is non-negotiable — every CI change must preserve the correctness of model results and not hide failures.

MPAS has been maintained with consistent coding conventions and project structure over many years. Follow the style of existing code. Do not introduce patterns, naming conventions, or organizational choices that diverge from what is already in the repository.

## Purpose of CI

The CI exists to support code health for a community model. Scientists and students — not just software engineers — need to understand and use these workflows. Keep configurations readable, well-commented, and avoid unnecessary abstraction.

## Repository Layout

- `.github/actions/` — Reusable composite actions (build-mpas, run-mpas, run-perturb-mpas, download-testdata, validate-logs)
- `.github/workflows/` — GitHub Actions workflow definitions
- `.github/workflows/validation/` — Python scripts for log comparison
- `.github/test-cases/` — Test case configurations (`240km/`, `ect-120km/`), each with a `config.env`
- `NCAR/mpas-ci-data` — External public repo (Git LFS) hosting test case archives and ECT summary files

## Modularity

Workflows must stay modular. Reusable logic belongs in composite actions under `.github/actions/`, not duplicated across workflow files. Current actions:

- **build-mpas** — Compiles MPAS-A for a given compiler family. Build logic is inlined in the action, not in external shell scripts.
- **download-testdata** — Downloads and extracts a test case archive from `NCAR/mpas-ci-data`. Reads `RESOLUTION` and `DATA_REPO` from the test case's `config.env`.
- **run-mpas** — Configures and runs MPAS-A (calls `download-testdata` internally). Supports `strict-exit-check: 'false'` to tolerate non-zero exit codes (e.g., gfortran IEEE warnings). **Important**: sourcing `config.env` overwrites the `RESOLUTION` shell variable — the action saves and restores the input value so `WORKDIR` uses the test-case name (e.g., `run-ect-120km`), not the archive name (`run-120km`).
- **run-perturb-mpas** — Runs one or more perturbed MPAS-A ensemble members for ECT. Contains `perturb_theta.py` (IC perturbation) and `trim_history.py` (history file trimming). Resolution-specific exclusion lists remain in `.github/test-cases/<res>/ect_excluded_vars.txt`. Supports both single-member runs (`member-start == member-end`) and batched runs. Used by `ect-test.yml` and `ect-ensemble-gen.yml`. When a `restart-file` is provided, the action extracts the `xtime` variable to rename the file to MPAS's expected `restart.YYYY-MM-DD_HH.MM.SS.nc` format, creates the required `restart_timestamp` file, and sets `config_do_restart = .true.` / `config_start_time = 'file'`. The `output` stream interval is set to `RUN_DURATION` and `restart` stream output is disabled for perturbed members.
- **validate-logs** — Compares run logs against reference output.

When adding new functionality, check whether it should be a new composite action or belongs in an existing one. Do not put reusable shell logic in standalone `.sh` scripts under `.github/workflows/` — that pattern caused breakage when scripts were cleaned up but actions still referenced them. Keep all build, download, and run logic self-contained within actions.

## Container Environment

All builds and runs use NCAR Docker containers: `ncarcisl/cisldev-x86_64-almalinux9-{compiler}-{mpi}:devel`

Key facts about these containers:
- `python` is not on PATH; always use `python3`
- `pip` is not on PATH; use `python3 -m ensurepip --upgrade 2>/dev/null || true` then `python3 -m pip install ...`
- `/container/config_env.sh` must be sourced before running MPI executables
- `free` may not be available in all containers

## MPI Compatibility Matrix (4-rank, 240km, GitHub Actions runners)

| Compiler | MPI | 1-proc | 4-proc | Notes |
|----------|-----|--------|--------|-------|
| gcc | openmpi | pass | pass | Needs `--allow-run-as-root --oversubscribe` |
| gcc | mpich3 | pass | **fail** | Heap corruption during mesh bootstrap |
| nvhpc | openmpi | pass | **fail** | malloc assertion in nvhpc Fortran runtime |
| nvhpc | mpich3 | pass | pass | |
| oneapi | openmpi | pass | pass | Needs `--allow-run-as-root --oversubscribe` |
| oneapi | mpich3 | pass | pass | |

The gcc/mpich3 and nvhpc/openmpi 4-proc failures are maybe container library issues, not MPAS bugs. They crash with glibc heap corruption during SMIOL parallel I/O initialization. All combinations pass at 1 rank.

**ECT workflows use gcc/openmpi** because it works at both 1 and 4 ranks with gfortran.

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

## Ensemble Consistency Test (ECT)

ECT validates that code changes do not alter model output beyond internal variability. It does not require bit-for-bit reproducibility — scientifically equivalent changes pass. Reference: Price-Broncucia et al. (2025), doi:10.5194/gmd-18-2349-2025.

ECT workflows:
- `ect-ensemble-gen.yml` — Generates N perturbed runs and produces a PyCECT summary file (expensive, manual trigger)
- `ect-test.yml` — Standalone: runs 3 members against an existing summary file (fast, used for validation)
- `test-ga-nogpu.yml` — Embedded ECT: runs 3 perturbed members for every compiler/MPI/IO/num-procs combination alongside the existing 240km log-based validation
- `test-cirrus-nvhpc.yml` — Embedded ECT: runs 3 perturbed members for every MPI/GPU/IO combination alongside existing log validation

The embedded ECT jobs use the gcc-generated ensemble summary for all compiler/MPI/decomposition comparisons. Per the paper's authors, only one compiler is needed for ensemble generation — the summary should still detect meaningful changes across other compilers, MPI libraries, and decompositions.

Key constraints:
- **24-hour spin-up**: Hydrometeor fields are zero in cold-start `init.nc`. The ensemble generation workflow runs a 24h unperturbed simulation (4 MPI ranks, `strict-exit-check: 'false'`) first, then uses the restart file as the starting point for all perturbed members. The restart file is uploaded to `NCAR/mpas-ci-data` so `ect-test.yml` can download it. **MPAS restart requirements**: restart mode needs (1) a file named `restart.YYYY-MM-DD_HH.MM.SS.nc` matching the filename template in `streams.atmosphere`, and (2) a `restart_timestamp` text file containing that timestamp. The `run-perturb-mpas` action handles both automatically. See Price-Broncucia et al. (2025), Section 3.2.
- **PyCECT requires ensemble size >= number of output variables** (~47 after trimming for the 120km case; minimum 48). The default of 200 members is recommended. The tool exits 0 even on failure — always verify the output file exists.
- History files are trimmed before upload: `run-perturb-mpas/trim_history.py` extracts a single time slice and removes variables listed in `ect_excluded_vars.txt` (PV diagnostics, integers, edge velocity). This keeps artifact sizes manageable for 200-member ensembles.
- **PyCECT `--jsonfile` path pitfall**: `pyEnsSumMPAS.py` writes auto-detected exclusions to `NEW.<jsonfile>`. If `--jsonfile` includes a directory (e.g., `pycect/exclude.json`), it tries to create `NEW.pycect/exclude.json` — a nonexistent directory — and crashes. Always pass a filename in the working directory, not a subdirectory path.
- **ECT perturbation magnitude**: The paper recommends O(1e-14) for theta perturbations, matching CESM convention. This requires a run long enough (6 hours) for perturbations to propagate across all fields. Magnitudes of 1e-1 or larger cause NaN divergence.
- ECT configuration lives in `.github/test-cases/ect-120km/config.env`
- Summary files and the spin-up restart are versioned and uploaded to `NCAR/mpas-ci-data` with metadata (requires `MPAS_CI_DATA_TOKEN` secret with repo scope)
- The `output` stream in `streams.atmosphere` defaults to `output_interval="none"` — ECT workflows must override this via sed to produce history files

## workflow_dispatch Visibility

GitHub only shows the workflow_dispatch trigger button for workflows defined on the **default branch** (master). When adding or modifying workflow_dispatch workflows on feature branches, the workflow file must also exist on master for the UI button to appear. Sync workflow files to master when needed.

## Common Pitfalls

1. **Large files**: Test case archives (>100MB) cannot be stored in the repo. They go in `NCAR/mpas-ci-data` with Git LFS and are downloaded at runtime via curl.
2. **Matrix job dependencies**: `needs: build` with matrix jobs causes all run jobs to skip if any build fails. Use `if: ${{ !cancelled() }}` on the dependent job to allow partial runs.
3. **Artifact patterns**: Use `continue-on-error: true` on artifact download steps and gate subsequent steps with `if: steps.<id>.outcome == 'success'` to handle missing artifacts gracefully.
4. **YAML heredocs**: EOF terminators at column 1 inside run blocks can confuse the YAML parser. Use string concatenation for multi-line commit messages instead.
5. **Registry.xml version extraction**: The file contains both `<?xml version="1.0"?>` and `<registry ... version="8.3.1">`. Use `grep -oP '<registry.*version="\K[^"]+'` to target only the registry version.
6. **config.env variable clobbering**: Sourcing `config.env` sets shell variables like `RESOLUTION=120km`. If a calling script already has a `RESOLUTION` variable (e.g., `ect-120km`), it gets overwritten. Always save variables you need before sourcing, or restore them after.
7. **MPAS restart_timestamp**: When `config_do_restart = .true.`, MPAS reads a `restart_timestamp` text file to determine which restart file to open (matching the `filename_template` in the restart stream). Without this file the model immediately crashes with a Fortran runtime error. The file contains a single line like `2010-10-24_00:00:00`.
8. **Default MPI ranks**: ECT ensemble generation uses 4 MPI ranks (requires `graph.info.part.4` in the test case archive). The 120km archive includes partition files for 4, 36, and 128 ranks.
