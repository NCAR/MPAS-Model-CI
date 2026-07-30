# MPAS-A Continuous Integration — Current Status Summary

*Prepared for sharing with NOAA/GSL collaborators*
*NCAR Mesoscale & Microscale Meteorology Laboratory*
*March 2026*

---

## Executive Summary

NCAR has developed a comprehensive CI system for MPAS-Atmosphere that
automatically builds, runs, and validates the model across 48+
configurations spanning three compilers, three MPI libraries, two I/O
layers, and both CPU and GPU code paths. The system includes an
Ensemble Consistency Test (ECT) that statistically detects
science-altering code changes without requiring bit-for-bit
reproducibility. The CI infrastructure can test commits in the
authoritative `MPAS-Dev/MPAS-Model` repository today and is designed
for eventual migration into that repository.

## Repository

- **CI infrastructure**: [NCAR/MPAS-Model-CI](https://github.com/NCAR/MPAS-Model-CI)
  (fork of MPAS-Dev/MPAS-Model, branch `feature-ci-test-cases`, 70 commits)
- **Test data**: [NCAR/mpas-ci-data](https://github.com/NCAR/mpas-ci-data)
  (test case archives, ensemble summary files, spin-up restarts)
- **Contributor's Guide**: [contributors-mpas-a.readthedocs.io](https://contributors-mpas-a.readthedocs.io/)

## Test Coverage

### Main CI Workflow (GitHub Actions hosted runners)

Builds and runs MPAS-A across a full matrix of configurations:

| Dimension    | Values                                      | Count |
|--------------|---------------------------------------------|-------|
| Compilers    | GCC (gfortran), NVHPC (nvfortran), Intel OneAPI (ifx) | 3 |
| MPI libraries| MPICH 3, MPICH 4, OpenMPI                   | 3     |
| I/O layers   | SMIOL, PIO                                  | 2     |
| MPI ranks    | 1 process, 4 processes                      | 2     |

**18 build configurations × 2 decompositions = 36 test runs**

Each run:
- Executes a 6-hour forecast on a 240km global mesh
- Validates output logs against a reference log
- Compares 1-process and 4-process output (decomposition consistency)

### GPU Testing (CIRRUS self-hosted runners)

NVHPC compiler with GPU (CUDA/OpenACC) and CPU-only code paths:

| Dimension    | Values                                      | Count |
|--------------|---------------------------------------------|-------|
| GPU modes    | CPU-only (nogpu), GPU (CUDA/OpenACC)        | 2     |
| MPI libraries| MPICH 3, MPICH 4, OpenMPI                   | 3     |
| I/O layers   | SMIOL, PIO                                  | 2     |

**12 NVHPC configurations** on NCAR CIRRUS runners with NVIDIA GPU access.

### Ensemble Consistency Test (ECT)

ECT provides a statistically rigorous validation that goes beyond log
comparison. Based on the methodology described in Price-Broncucia et
al. (2025, GMD, [doi:10.5194/gmd-18-2349-2025](https://doi.org/10.5194/gmd-18-2349-2025)).

**How it works:**

1. A 200-member perturbed ensemble is generated once by applying
   O(10⁻¹⁴) perturbations to the potential temperature (theta) field
   in the initial conditions, then running 6-hour forecasts on a
   120 km mesh from a 24-hour spun-up restart
2. Ensemble statistics are computed and stored as a summary file using
   PyCECT (v3.3.1)
3. For each CI run, 3 perturbed members are generated for the code
   under test and compared against the ensemble summary

**Key property:** ECT does not require bit-for-bit reproducibility.
Changes that are scientifically equivalent (optimization, refactoring,
build-system changes) pass. Changes that alter the model's physical
behavior beyond internal variability are flagged.

ECT runs for **every** compiler/MPI/I/O combination in the main CI
workflows, with results collected into a consolidated summary table.

### Code Coverage

A separate workflow builds MPAS-A with GCC coverage instrumentation,
runs a standard test case, and uploads results to Codecov for tracking
coverage trends over time.

## CI Architecture

### Containerized Builds

All builds and runs execute inside NCAR CISL Docker containers hosted on
Docker Hub. Each container includes a specific compiler, MPI library,
and pre-built I/O dependencies (NetCDF, Parallel-NetCDF, PIO).

- **Base OS**: AlmaLinux 9
- **Image pattern**: `ncarcisl/cisldev-x86_64-almalinux9-{compiler}-{mpi}:devel`
- **Platform**: GitHub Actions hosted runners (free for public repos)
  and NCAR CIRRUS self-hosted runners (GPU)
- **No HPC dependency**: Does not require Derecho, Cheyenne, or any
  HPC scheduler

### Modular Design

The CI system uses 7 reusable composite actions:

| Action              | Purpose                                         |
|---------------------|-------------------------------------------------|
| `build-mpas`        | Compile MPAS-A for any supported compiler       |
| `download-testdata` | Download and cache test case archives           |
| `run-mpas`          | Configure namelist/streams and run the model    |
| `run-perturb-mpas`  | Run perturbed ensemble members for ECT          |
| `validate-logs`     | Compare output logs against reference           |
| `validate-ect`      | Run PyCECT validation against ensemble summary  |
| `ect-summary`       | Generate consolidated ECT results table         |

Test case parameters are externalized in configuration files. Adding a
new test case or resolution requires adding a new config directory —
no workflow modifications are needed.

### Cross-Repository Testing

All workflows accept `mpas-repository` and `mpas-ref` inputs via
GitHub's manual workflow trigger. This allows testing any commit,
branch, or tag in any public MPAS repository (e.g.,
`MPAS-Dev/MPAS-Model`) using the CI infrastructure in
`NCAR/MPAS-Model-CI`.

Example (GitHub CLI):

```bash
gh workflow run test-ga-nogpu.yml \
  -R NCAR/MPAS-Model-CI \
  --ref feature-ci-test-cases \
  -f mpas-repository="MPAS-Dev/MPAS-Model" \
  -f mpas-ref="develop"
```

This provides an operational interim solution while the timeline for
migrating CI directly into the authoritative repository is determined.

## 5 Workflows

| Workflow                | Purpose                                     | Trigger        |
|-------------------------|---------------------------------------------|----------------|
| `test-ga-nogpu.yml`     | Full matrix build/run/validate + ECT        | Manual, push   |
| `test-cirrus-nvhpc.yml` | NVHPC GPU/CPU testing + ECT                 | Manual, push   |
| `ect-test.yml`          | Standalone ECT (3 members, gcc/openmpi)     | Manual, push   |
| `ect-ensemble-gen.yml`  | Generate 200-member ensemble summary        | Manual only    |
| `coverage.yml`          | Code coverage with Codecov                  | Manual, push   |

## Comparison with GSL CI

| Capability                  | NCAR (MPAS-Model-CI)         | GSL (UFS fork)              |
|-----------------------------|------------------------------|-----------------------------|
| **Compilers**               | GCC, NVHPC, Intel OneAPI     | GNU (19 tests), Intel (1)   |
| **GPU testing**             | Yes (CUDA/OpenACC via NVHPC) | In development              |
| **Container-based**         | Yes (NCAR CISL Docker)       | In development              |
| **Statistical validation**  | Yes (ECT, 200-member PyCECT) | No                          |
| **Regression tests**        | Log comparison               | 9 configs × 2 opt levels   |
| **Test resolution**         | 240km (standard), 120km (ECT)| 120km CONUS                 |
| **Physics configurations**  | Default                      | meso_ref, conv_perm, hrrrv5, noahmp |
| **Platform**                | GitHub Actions + CIRRUS      | GitHub Actions + EMC Intel  |
| **Cross-repo testing**      | Yes (any fork/branch/SHA)    | Baseline vs feature branch  |

**Complementary strengths**: NCAR provides broader compiler/GPU coverage
and statistical science validation (ECT). GSL provides broader physics
configuration testing and regression baselines. Combining these would
give the community model comprehensive CI coverage.

## Collaboration Opportunities

1. **Shared container infrastructure**: Both teams are building
   containerized CI environments with similar compiler/MPI stacks.
   Sharing or co-maintaining container images would reduce duplication.

2. **Shared test data**: Both test at 120km resolution. Test case
   archives and ensemble summary files could be hosted in a common
   location.

3. **Complementary test suites**: NCAR's ECT catches statistical
   changes across all variables; GSL's regression tests validate
   specific physics configurations. Running both provides defense
   in depth.

4. **Cross-repo testing for authoritative repo**: The `mpas-repository`
   / `mpas-ref` input mechanism allows NOAA to trigger NCAR CI against
   any `MPAS-Dev/MPAS-Model` commit today, without modifying the
   upstream repository.

5. **Path to PR-triggered CI**: Once workflows are migrated into
   `MPAS-Dev/MPAS-Model`, CI can run automatically on every pull
   request, giving all community contributors immediate feedback.

## Timeline Considerations

| Phase         | Description                                    | Status        |
|---------------|------------------------------------------------|---------------|
| **Current**   | CI operational in NCAR/MPAS-Model-CI; can test upstream commits via cross-repo inputs | Working today |
| **Short-term**| Share/demo with NOAA; coordinate on containers and test cases | Ready |
| **Medium-term**| Migrate workflows into MPAS-Dev/MPAS-Model; coordinate with GSL on shared infrastructure | Requires repo admin access and coordination |
| **Longer-term**| PR-triggered CI on authoritative repo; shared ensemble summaries; additional resolutions and physics configs | Planning |

## Contact

- Cena Brown, NCAR — [email]
- Sheri Voelz, NCAR — mickelso@ucar.edu
- Michael Duda, NCAR — duda@ucar.edu
