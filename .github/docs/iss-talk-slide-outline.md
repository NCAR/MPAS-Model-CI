# MPAS-A CI/CD — ISS Talk Slide Outline

*Target audience: NCAR colleagues, NOAA/GSL collaborators, atmospheric scientists*
*Can be shared externally with NOAA as-is or adapted*

---

## Slide 1: Title

**Continuous Integration for MPAS-Atmosphere**

- Cena Brown, NCAR
- ISS Talk, [date TBD]
- Collaboration with: Sheri Voelz, Michael Duda, [others]

---

## Slide 2: Motivation — Why CI for MPAS?

- MPAS-A is a community model used for weather prediction and research
- Code changes can introduce subtle scientific errors that are hard to
  catch in code review alone
- Multiple compilers, MPI libraries, I/O layers, and decompositions
  must all produce consistent results
- Manual testing doesn't scale — automated CI catches regressions before
  they reach the community

*Talking point: NOAA/GSL is also investing in CI for the UFS fork of MPAS
(Ligia Bernardet's team). Opportunity for shared infrastructure.*

---

## Slide 3: What the CI System Does

Four stages, fully automated:

1. **Build** — compile MPAS-A across multiple compiler/MPI/I/O combinations
2. **Run** — execute a standard test case at 1-process and 4-process decompositions
3. **Validate** — compare output logs against reference values
4. **Ensemble Consistency Test** — statistically verify that model output
   has not changed beyond internal variability

*Include the Mermaid pipeline diagram (rendered to image):*

```
Build → Run → Validate → Cleanup
      → ECT Run → ECT Validate → ECT Summary
```

---

## Slide 4: Test Matrix — What Gets Tested

**GitHub Actions hosted runners (test-ga-nogpu.yml):**

| Dimension    | Options                            | Count |
|--------------|------------------------------------|-------|
| Compilers    | GCC, NVHPC, Intel OneAPI           | 3     |
| MPI          | MPICH 3, MPICH 4, OpenMPI          | 3     |
| I/O layers   | SMIOL, PIO                         | 2     |
| MPI ranks    | 1, 4                               | 2     |

= **36 test configurations** per workflow run

**CIRRUS self-hosted runners (test-cirrus-nvhpc.yml):**

| Dimension    | Options                            | Count |
|--------------|------------------------------------|-------|
| GPU modes    | CPU-only, GPU (CUDA/OpenACC)       | 2     |
| MPI          | MPICH 3, MPICH 4, OpenMPI          | 3     |
| I/O layers   | SMIOL, PIO                         | 2     |

= **12 NVHPC configurations** (CPU and GPU code paths)

*Talking point: GSL currently has 20 tests, mostly GNU-based.
Our matrix covers 3 compilers and GPU. Complementary coverage.*

---

## Slide 5: Containerized Environment

- All builds and runs execute inside NCAR CISL Docker containers
- Each container ships a specific compiler + MPI library + I/O stack
  (NetCDF, Parallel-NetCDF, PIO)
- Image pattern: `ncarcisl/cisldev-x86_64-almalinux9-{compiler}-{mpi}:devel`
- Runs on GitHub-hosted runners (free for public repos) and NCAR CIRRUS
  self-hosted runners (GPU access)
- No dependency on Derecho, Cheyenne, or any HPC scheduler

*Talking point: GSL is also developing containerized CI.
Container images could potentially be shared.*

---

## Slide 6: Ensemble Consistency Test (ECT) — The Science Check

- **Problem**: Code changes can alter model physics in ways that aren't
  visible in log comparisons or bit-for-bit checks
- **Solution**: ECT (Price-Broncucia et al., 2025, GMD)
  - Generate a 200-member perturbed ensemble (O(10⁻¹⁴) theta perturbations)
  - Compute ensemble statistics (PyCECT)
  - For each new code change, run 3 perturbed members and compare
  - PASSED = output is within the ensemble's internal variability
  - FAILED = statistically significant change detected

*Key point: Does NOT require bit-for-bit reproducibility.
Refactoring and optimization changes pass. Science changes are caught.*

---

## Slide 7: ECT — How It's Integrated

- ECT runs for **every** compiler/MPI/I/O combination in the main CI
  workflows — not just one compiler
- Per the paper's authors: one compiler's ensemble (gcc) is sufficient
  for detecting meaningful changes across all compilers/MPI libraries
- Results collected into a consolidated summary table in the GitHub
  Actions UI

*Show screenshot of ECT summary table from a real workflow run*

---

## Slide 8: Cross-Repository Testing

- CI infrastructure currently lives in `NCAR/MPAS-Model-CI` (fork)
- Can test **any commit** in `MPAS-Dev/MPAS-Model` without modifying
  the upstream repo

```
gh workflow run test-ga-nogpu.yml \
  -f mpas-repository="MPAS-Dev/MPAS-Model" \
  -f mpas-ref="develop"
```

- Build job checks out MPAS source from the target repo, overlays
  CI infrastructure from MPAS-Model-CI
- **Bridge to the future**: when CI moves to the authoritative repo,
  the workflows and composite actions transfer directly

*Talking point: This is our answer to "timeline for CI on the
authoritative repo" — it works today as an interim solution.*

---

## Slide 9: Code Coverage

- GCC build with `--coverage` flags
- Runs 240km test case, generates lcov report
- Uploads to Codecov for tracking coverage trends over time
- Helps identify untested code paths

---

## Slide 10: Architecture — Modular and Reusable

7 composite actions encapsulate reusable logic:

| Action           | Purpose                                          |
|------------------|--------------------------------------------------|
| `build-mpas`     | Compile MPAS-A for any supported compiler        |
| `download-testdata` | Download + cache test case archives           |
| `run-mpas`       | Configure namelist/streams and run the model     |
| `run-perturb-mpas` | Run perturbed ensemble members for ECT        |
| `validate-logs`  | Compare output logs against reference            |
| `validate-ect`   | Run PyCECT against ensemble summary              |
| `ect-summary`    | Generate consolidated ECT results table          |

All configuration is externalized in `config.env` files per test case.
Adding a new test case or resolution = new config directory, no workflow changes.

---

## Slide 11: Documentation

- **Contributor's Guide**: https://contributors-mpas-a.readthedocs.io/
  - CI/CD page auto-generated from actual workflow files
  - Generator script (`generate_ci_docs.py`) ensures docs never drift
    from implementation
- **CI layout**: Workflows and composite actions under `.github/`, central config in `.github/ci-config.env`
- **Testing upstream commits**: Step-by-step guide for cross-repo testing

---

## Slide 12: Comparison with GSL CI

| Capability                  | NCAR (MPAS-Model-CI)       | GSL (UFS fork)            |
|-----------------------------|----------------------------|---------------------------|
| Compilers                   | GCC, NVHPC, Intel          | GNU (19 tests), Intel (1) |
| GPU testing                 | Yes (CUDA/OpenACC)         | In development            |
| Container-based             | Yes (CISL Docker)          | In development            |
| Statistical validation (ECT)| Yes (PyCECT, 200-member)   | No                        |
| Regression tests            | Log comparison              | 9 configs × 2 opt levels |
| Test resolution             | 240km (standard), 120km (ECT) | 120km CONUS          |
| Physics configurations      | Default                    | meso_ref, conv_perm, hrrrv5, noahmp |
| Platform                    | GitHub Actions + CIRRUS     | GitHub Actions + EMC Intel |
| Cross-repo testing          | Yes (any fork/branch/SHA)  | Baseline vs feature branch |

*Talking point: Clear complementary strengths. NCAR has broader
compiler/GPU coverage and ECT. GSL has broader physics configurations
and regression baselines. Combining these would give the community
model comprehensive CI.*

---

## Slide 13: Path Forward — Timeline for Authoritative Repo

**Current state (working today):**
- CI workflows in `NCAR/MPAS-Model-CI` can test any `MPAS-Dev/MPAS-Model` commit
- 70 commits of CI development on `feature-ci-test-cases` branch

**Short-term (shareable now):**
- Demo cross-repo testing for NOAA
- Share container images and composite action patterns with GSL

**Medium-term:**
- Migrate workflows into `MPAS-Dev/MPAS-Model` (requires repo admin access)
- Coordinate with GSL on shared test cases and container infrastructure
- Add GSL physics configurations to test matrix

**Longer-term:**
- PR-triggered CI on the authoritative repo
- Shared ensemble summary files across NCAR and NOAA testing
- Expand to additional resolutions and platforms

---

## Slide 14: Summary

- MPAS-A CI is **operational today** with 48+ test configurations
  across 3 compilers, 3 MPI libraries, CPU and GPU
- **ECT** provides a statistically rigorous science check that goes
  beyond bit-for-bit comparison
- **Cross-repo testing** bridges the gap until CI lives in the
  authoritative repo
- **Modular architecture** (7 composite actions, externalized configs)
  makes it straightforward to extend
- Ready to collaborate with NOAA/GSL on shared infrastructure

---

## Backup Slides

### B1: ECT Technical Details
- 200-member ensemble, O(10⁻¹⁴) theta perturbations
- 120km mesh, 6-hour forecasts from 24-hour spun-up restart
- PyCECT v3.3.1 for statistical comparison
- Reference: Price-Broncucia et al. (2025), doi:10.5194/gmd-18-2349-2025

### B2: Container Image Details
- Base: AlmaLinux 9
- Compilers: GCC (gfortran), NVHPC (nvfortran), Intel OneAPI (ifx)
- MPI: MPICH 3.x, MPICH 4.x, OpenMPI
- I/O: NetCDF-C/Fortran, Parallel-NetCDF, PIO
- Registry: Docker Hub `ncarcisl/cisldev-x86_64-*`

### B3: Known Container Issues
- gcc + mpich 4-proc: heap corruption during mesh bootstrap
- nvhpc + openmpi 4-proc: malloc assertion in Fortran runtime
- These are container library issues, not MPAS bugs
