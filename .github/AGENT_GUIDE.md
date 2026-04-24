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
├── data/
│   └── ect_excluded_vars.txt    # ECT variable exclusion list (PyCECT)
├── actions/
│   ├── build-mpas/              # Compiles MPAS-A for a given compiler
│   ├── checkout-mpas-source/    # Cross-repo checkout with CI overlay
│   ├── download-testdata/       # Downloads + caches test case archives
│   ├── resolve-container/       # Resolves container image from ci-config.env
│   ├── setup-nsight-systems/    # Install/cache Nsight Systems CLI (nsys) on EL GPU images
│   ├── run-mpas/                # Configures and runs MPAS-A
│   ├── run-perturb-mpas/        # Runs perturbed ensemble members for ECT
│   │   ├── perturb_theta.py     # IC perturbation (theta field)
│   │   └── trim_history.py      # Trims history files for artifact upload
│   ├── print-mpas-logs/         # Dumps log.atmosphere.* into ::group:: blocks
│   ├── validate-ect/            # PyCECT validation
│   └── ect-summary/             # Consolidated ECT results table
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
    ├── compile-nvhpc-cuda-mpich.yml  # NVHPC+MPICH+CUDA compile-only (GA-hosted)
    ├── profile-gpu-nsight.yml        # Nsight Systems profile on CIRRUS (dispatch-only)
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

## Test Data

Test case archives, ECT ensemble summary files, and ECT spin-up restarts are stored as **GitHub release assets on this repository** (`NCAR/MPAS-Model-CI`). Each asset is versioned by its own release tag (independent of the others).

Current tags: `testdata-240km-v1`, `testdata-120km-v1` (see `RELEASE_TESTDATA_*` in `ci-config.env`), plus `ect-v{MPAS_VERSION}` for ECT data — its tag is derived at runtime from `src/core_atmosphere/Registry.xml` via the `mpas-version` composite action, not from `ci-config.env`.

**Adding a new test case:** build the archive (`{resolution}.tar.gz`), create a release (`gh release create … --repo NCAR/MPAS-Model-CI`), attach the asset, then set `RELEASE_TESTDATA_{RES}` in `ci-config.env` (resolution uppercased with `-` → `_` in the variable name, e.g. `120KM`).

`namelist.atmosphere` inside each archive carries model defaults; workflows override only what they need.

## Branch Structure

- **`master`** — default branch, mirrors upstream MPAS-Model. Workflow files must exist here for the `workflow_dispatch` UI button to appear.
- **`develop`** — upstream develop branch.
- **Topic branches** — fork from `master` for changes. Branches named **`hackathon-*`** auto-run **CPU ECT subsets** (push/PR). **GPU ECT** stays **`workflow_dispatch` only** (see Security). CPU BFB callers also run on push to `hackathon`, `hackathon/**`, `hackathon-*`, or legacy `feature-ci-bfb`.

## Workflow Architecture

### Subset Workflows (primary CI)

Each compiler+MPI combination has a thin caller workflow that invokes a reusable template:

- **CPU subsets** call `_test-compiler.yml` with `compiler` and `mpi` inputs
- **GPU subsets** call `_test-gpu.yml` with `mpi` input (always NVHPC)

**MPICH callers** (`test-gcc-mpich`, `test-intel-mpich`, `test-nvhpc-mpich`) run on push/PR to `master`/`develop` and to **`hackathon-*`**.
**compile-nvhpc-cuda-mpich** (NVHPC + OpenACC compile-only on GitHub-hosted runners) also runs on push/PR to those branches.
**OpenMPI CPU callers** (`test-*-openmpi`) stay **`workflow_dispatch` only** (optional; OpenMPI regressions).
**GPU ECT callers** (`test-gpu-mpich`, `test-gpu-openmpi`) are **`workflow_dispatch` only** (self-hosted CIRRUS).

### _test-compiler.yml — Reusable CPU Workflow

**Job flow**: `config` → `build` → `ect-run` (3 parallel members) → `ect-validate` → `cleanup`

- Builds in double precision with SMIOL I/O
- Runs 3 perturbed ensemble members in parallel (matrix strategy), each with 4 MPI ranks
- Validates with PyCECT against the ensemble summary file
- If build fails, ECT jobs skip (explicit `needs.build.result == 'success'` check)

### _test-gpu.yml — Reusable GPU Workflow

Same structure as `_test-compiler.yml` but builds with OpenACC (`openacc: 'true'`) and runs on `CIRRUS-4x8-gpu` self-hosted runners.

### compile-nvhpc-cuda-mpich.yml — CUDA toolchain (compile-only)

Runs on **GitHub-hosted** `ubuntu-latest` inside `CONTAINER_IMAGE_GPU` (NVHPC + MPICH + CUDA). Builds MPAS-A with `openacc: 'true'` and double precision — **no GPU and no model run**. Supplements `_test-gpu.yml` (full ECT on CIRRUS) by catching toolchain breakage on every push/PR.

### profile-gpu-nsight.yml — Nsight Systems (GPU)

**`workflow_dispatch` only** on `CIRRUS-4x8-gpu` (same security model as `test-gpu-*.yml`). Resolves the CUDA container, builds OpenACC MPAS-A, downloads a test case, and overrides **`config_run_duration` only** (`config_dt` is never changed — it is set by science for each resolution). Defaults use the **240km** test archive with **`0_01:00:00`**, i.e. **three timesteps** for the stock **240km** case (`config_dt = 1200s`, same duration convention as BFB on 240km). The profile job runs `.github/actions/setup-nsight-systems` so a working **`nsys`** is available: if the image already exposes Nsight Systems or CUDA `nsys`, that is used; otherwise the **`nsight-systems-cli`** RPM set is installed from NVIDIA’s devtools repo (Alma/RHEL-family images), with downloaded RPMs cached under `.cache/nsight-systems-rpms` (bump `NSYS_CLI_CACHE_VERSION` in `ci-config.env` to invalidate). Then `.github/scripts/run-nsys-profile.sh` runs `nsys profile --trace=cuda,nvtx,osrt --stats=true` around `mpirun`. Uploads the session file (`.nsys-rep` / `.qdrep`) and `nsys stats` text with **3-day** artifact retention. For other resolutions, set `run_duration` to at least one timestep for that case’s `config_dt`.

### Other Workflows

- **ect-test.yml** — standalone 3-member ECT (gcc/openmpi). Kept for debugging.
- **ect-ensemble-gen.yml** — generates the PyCECT ensemble summary file (~200 model runs). Manual trigger only.
- **coverage.yml** — GCC build with `--coverage`, 240km test case, Codecov upload. Runs on push to master.
- **unit-tests.yml** — pFUnit tests across GCC 12/13/14 matrix.

## Configuration: ci-config.env

All container images, compiler mappings, MPI flags, per-asset release tags, ECT parameters, and BFB test stubs are centralized in `.github/ci-config.env`. Workflows source this file via the `resolve-container` composite action and/or `source` in composite steps.

Key settings:
- `CONTAINER_IMAGE` / `CONTAINER_IMAGE_GPU` — image templates with `{compiler}` and `{mpi}` placeholders
- `CONTAINER_IMAGE_{compiler}` — optional per-compiler image template overrides
- `CONTAINER_COMPILER_{name}` — name mappings when image tags differ (e.g., `gcc` → `gcc14`)
- `MAKE_TARGET_{compiler}` — maps CI names to Makefile targets
- `NVHPC_EXTRA_MAKE_FLAGS` / `ONEAPI_EXTRA_MAKE_FLAGS` — compiler-specific build workarounds
- `OPENMPI_RUN_FLAGS` — extra `mpirun` flags for OpenMPI in containers (root + oversubscribe). MPICH needs no equivalent. Comment in `ci-config.env` lists the consumer sites for adding analogous flags later.
- `RELEASE_TESTDATA_{RES}` — GitHub release tag for `{resolution}.tar.gz` test archives (`RES` uppercased, `-` → `_`)
- `ECT_*` — ECT resolution, perturbation, summary/restart filenames, excluded-vars path, etc.
- The ECT release tag (`ect-v{MPAS_VERSION}`) is **not** stored here; it is derived at runtime from `src/core_atmosphere/Registry.xml` by the `mpas-version` composite action (see below). This guarantees the writer (`ect-ensemble-gen.yml`) and readers (`_test-compiler.yml`, `_test-gpu.yml`, `ect-test.yml`, `validate-ect`) can never drift apart.
- `PYCECT_TAG` — PyCECT git tag for `validate-ect`
- `BFB_*` — default resolution, duration, and run timeout for bit-for-bit workflows; per-variant overrides live in the `variants` JSON passed to `_test-bfb.yml`

### Bit-for-bit (`_test-bfb.yml`)

The reusable workflow `_test-bfb.yml` takes a **`variants`** input: a JSON **array** of at least two objects. Each object describes one model run:

| Field | Required | Meaning |
|-------|----------|---------|
| `id` | yes | Unique slug (letters, digits, `.`, `_`, `-`); used for artifacts and working directories |
| `ranks` | yes | MPI process count for that run |
| `use_pio` | no | If true, build/link PIO for that variant’s build profile (default false = SMIOL) |
| `openacc` | no | Per-variant OpenACC + CUDA/CIRRUS vs CPU/GitHub-hosted; omitted variants use workflow **`gpu`** input (`true` = all GPU, `false` = all CPU). Set **`gpu: 'false'`** and explicit **`openacc`** on each variant to mix NVHPC CPU and GPU (**`bfb-nvhpc-cpu-vs-gpu.yml`**) |
| `label` | no | Short description for logs and the compare summary (defaults to `id`) |
| `resolution` | no | Test case resolution for that run only (defaults to workflow `resolution` / `BFB_RESOLUTION`) |
| `run_duration` | no | `config_run_duration` for that run only (defaults to workflow `run-duration` / `BFB_RUN_DURATION`) |

Variants that share the same **`use_pio`** and **`openacc`** mode reuse one compiled executable (when both CPU and OpenACC builds exist in one workflow, artifact names gain `-cpu` / `-openacc` suffixes). The variant at **`reference_index`** (default **0**) is the reference; every other variant’s history file is compared to it (variable data, not raw file bytes — see `.github/scripts/compare-bfb-nc.py`).

**GPU BFB (uniform OpenACC):** set workflow input **`gpu: 'true'`** (string). `_test-bfb.yml` uses the CUDA image, **`openacc: true`** for every variant, and **`CIRRUS-4x8-gpu`** for build/run. **`compiler` must be `nvhpc`**. Precision is typically **`double`**. Example callers: **`bfb-decomp-gpu.yml`**, **`bfb-io-gpu.yml`**. Do **not** add `pull_request` triggers for GPU BFB — same policy as `_test-gpu.yml`.

**Adding a new BFB test:** copy `bfb-io.yml`, `bfb-decomp.yml`, `bfb-io-gpu.yml`, `bfb-decomp-gpu.yml`, or **`bfb-nvhpc-cpu-vs-gpu.yml`**, set `name` and `on`, and edit **`variants`** (and `gpu` / `precision` / per-variant **`openacc`** when applicable). MPI rank count and PIO vs SMIOL are common examples only; any future per-run knob exposed on `variants` and implemented in `_test-bfb.yml` / composite actions can be combined the same way.

## Container Environment

All builds and runs use `ncarcisl/hpcdev-x86_64` Docker containers. Image names are resolved from `ci-config.env` templates.

Current containers:
- **GCC, NVHPC, Intel (OneAPI)**: `hpcdev-x86_64:almalinux9-{compiler}-{mpi}-26.02` (`CONTAINER_COMPILER_*` mappings apply, e.g. `gcc` → `gcc14`)
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

### download-testdata
Takes `resolution`, looks up `RELEASE_TESTDATA_{RES}` in `ci-config.env`, downloads `{resolution}.tar.gz` from this repo’s GitHub releases (with `actions/cache`), and extracts the archive.

### run-mpas
Runs a standard MPAS-A case: uses `download-testdata`, copies the extracted tree into the run working directory, and starts the model. No longer sources per-case `test-cases/…/config.env`; optional `run-duration` / `restart-interval` override namelist defaults from the archive.

### run-perturb-mpas
Runs perturbed ensemble members for ECT. Requires explicit `run-duration` and `run-timeout` inputs. Sources `ci-config.env` for ECT settings (perturbation variable/magnitude, excluded-vars path, etc.). Activates conda, installs netCDF4/numpy, loops through members applying theta perturbation, runs the model, and trims history files. Supports restart mode.

### validate-ect
Takes a required `mpas-version` input and builds the release tag as `ect-v{mpas-version}`. Sources `ci-config.env` for summary filename, time slice, and PyCECT tag (no `RELEASE_ECT` lookup). Downloads the summary from the matching release URL, installs deps, clones PyCECT at `PYCECT_TAG`, runs validation, and writes an enriched result file with dimension metadata.

### mpas-version
Reads the MPAS version string from `src/core_atmosphere/Registry.xml` using `python3` + `xml.etree.ElementTree`. Strict — fails the workflow if the file is missing or the `<registry version="…">` attribute cannot be parsed (no silent `unknown` fallback). Single source of truth for the `ect-v{MPAS_VERSION}` release tag used by `_test-compiler.yml`, `_test-gpu.yml`, `ect-test.yml`, `ect-ensemble-gen.yml`, and `validate-ect`. Workflows that consume the version typically extract it once in their `config` job and pass it to downstream jobs as a job output.

### print-mpas-logs
Dumps MPAS per-rank log files (`log.atmosphere.<rank>.out` / `.err`) to the workflow log inside collapsible `::group::` blocks so the GitHub Actions UI gives one expandable section per file. Inputs: `log-dir` (required), `pattern` (default `log.atmosphere.*`), `max-lines` (default empty = full file; set to N to `tail -n N`). Read-only and never fails on its own — call sites should add `if: always()` so logs print on both success and failure. Already wired into `run-mpas` (reads from the run working dir) and `run-perturb-mpas` (reads from `output-dir`, where the per-member loop has copied each rank's `.out` and `.err` before tearing down the rundir).

### setup-nsight-systems
Ensures a working `nsys` (Nsight Systems CLI) on EL-based GPU images: prefers an existing install, otherwise installs **`nsight-systems-cli`** from NVIDIA’s devtools RPM repo and caches downloaded RPMs for faster reruns (`NSYS_CLI_CACHE_VERSION` in `ci-config.env`).

## Ensemble Consistency Test (ECT)

ECT validates that code changes do not alter model output beyond internal variability. It does **not** require bit-for-bit reproducibility. Reference: Price-Broncucia et al. (2025), doi:10.5194/gmd-18-2349-2025.

Key constraints:
- **Perturbation magnitude**: O(1e-14) for theta, requires double precision
- **Spin-up restart**: cold-start `init.nc` has zero hydrometeors. Ensemble generation runs 24h unperturbed first, then perturbs from the restart.
- **PyCECT minimum members**: ensemble size must be >= number of output variables (~48). Default: 200.
- **Time slice**: `run-perturb-mpas` invokes `trim_history.py` with `--tslice (Time.size - 1)`, producing files with exactly **one** time dimension (`Time=1`). PyCECT (`pyCECT.py` and `pyEnsSumMPAS.py`) is then called with `--tslice 0` — the only valid index in a single-slice file. There is no `ECT_TSLICE` knob in `ci-config.env`; changing the effective slice would require editing `run-perturb-mpas` (not config). Slice 0 in a cold-start (untrimmed) run is the unintegrated initial state, which is why we trim before validation.
- ECT parameters and paths in `.github/ci-config.env` (`ECT_*`, `ECT_EXCLUDED_VARS`, `PYCECT_TAG`); the ECT release tag itself is derived at runtime from `Registry.xml` via the `mpas-version` composite action.

## Shell Scripting Notes

GitHub Actions runs bash with `set -e -o pipefail`:

- **SIGPIPE**: `tar tzf file.tar.gz | head -1` kills tar (exit 141). Append `|| true`.
- **mpirun exit codes**: gfortran may exit non-zero on IEEE warnings. Use `set +e`/`set -e` and check for output files.
- **OpenMPI in containers**: requires `--allow-run-as-root --oversubscribe` (configured in `ci-config.env`).
- **curl retries**: always use `--retry 5 --retry-delay 5` for large downloads.

## Cross-Repo Testing

Workflows accept `mpas-repository` and `mpas-ref` inputs for testing upstream MPAS-Dev commits. The `checkout-mpas-source` action handles the two-step checkout and CI overlay. Primary multi-compiler entry point: **`test-cross-repo.yml`**. See `.github/docs/testing-upstream-commits.md`.

## Security

- **Self-hosted runners**: GPU ECT workflows (`_test-gpu`, `test-gpu-*`) use **`workflow_dispatch` only**. Do **not** add `push` or `pull_request` triggers — unreviewed code could run on CIRRUS. **`profile-gpu-nsight`** is also `workflow_dispatch` only.
- **Secret isolation**: Test data is public release assets on this repo, so CI does not need a separate data-repo PAT for downloads.
- **Cross-repo execution**: `workflow_dispatch` with external repo inputs runs `make` from that repo. Acceptable since only write-access users can trigger it.

## Known Issues

- **NVHPC+OpenMPI**: model exits 134 (SIGABRT) on GA runners with 4 ranks. MPICH works. Caller workflows and reusable CPU/GPU jobs mark this combination `continue-on-error` until resolved.
- **NVHPC/Intel MPI F08 bindings**: broken with hpcdev MPI libraries. Both use `MPAS_MPI_F08=0` workaround.
