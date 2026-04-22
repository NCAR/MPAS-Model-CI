MPAS-v8.4.0
====

## CI Status

### Ensemble Consistency Test

MPICH subsets run on every push and PR. OpenMPI and GPU subsets are available via manual dispatch.
Each test builds in double precision, runs 3 perturbed ensemble members (4 MPI ranks), and validates with [PyCECT](https://github.com/NCAR/PyCECT).

Thanks to Teo Price-Broncucia and Allison Baker for their help on ensemble consistency testing. Methodology and background are given in Price-Broncucia et al. (2025), [*Geosci. Model Dev.*, 18, 2349–2372](https://gmd.copernicus.org/articles/18/2349/2025/).

| Compiler | MPI | Target | Status | Container |
|----------|-----|--------|--------|-----------|
| GNU | MPICH | CPU | [![GNU+MPICH (CPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gcc-mpich.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gcc-mpich.yml) | `hpcdev:almalinux9-gcc14-mpich-26.02` |
| GNU | OpenMPI | CPU | [![GNU+OpenMPI (CPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gcc-openmpi.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gcc-openmpi.yml) | `hpcdev:almalinux9-gcc14-openmpi-26.02` |
| Intel | MPICH | CPU | [![Intel+MPICH (CPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-intel-mpich.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-intel-mpich.yml) | `hpcdev:almalinux9-oneapi-mpich-26.02` |
| Intel | OpenMPI | CPU | [![Intel+OpenMPI (CPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-intel-openmpi.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-intel-openmpi.yml) | `hpcdev:almalinux9-oneapi-openmpi-26.02` |
| NVHPC | MPICH | CPU | [![NVHPC+MPICH (CPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-nvhpc-mpich.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-nvhpc-mpich.yml) | `hpcdev:almalinux9-nvhpc-mpich-26.02` |
| NVHPC | OpenMPI | CPU | [![NVHPC+OpenMPI (CPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-nvhpc-openmpi.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-nvhpc-openmpi.yml) | `hpcdev:almalinux9-nvhpc-openmpi-26.02` |
| NVHPC | MPICH | GPU | [![NVHPC+MPICH (GPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gpu-mpich.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gpu-mpich.yml) | `hpcdev:almalinux9-nvhpc-mpich-cuda-26.02` |
| NVHPC | OpenMPI | GPU | [![NVHPC+OpenMPI (GPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gpu-openmpi.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gpu-openmpi.yml) | `hpcdev:almalinux9-nvhpc-openmpi-cuda-26.02` |

**Compile-only** workflows verify the NVHPC + OpenACC + CUDA toolchain by building on a Github Action runner without a GPU


| Compiler | MPI | Target | Status | Container |
|----------|-----|--------|--------|-----------|
| NVHPC | MPICH | CUDA (compile) | [![NVHPC+MPICH+CUDA (compile-only)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/compile-nvhpc-cuda-mpich.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/compile-nvhpc-cuda-mpich.yml) | `hpcdev:almalinux9-nvhpc-mpich-cuda-26.02` |


### Additional testing 

Bit-for-bit (BFB) workflows compare history output in single precision for CPU runs (240km case; see the BFB section in [`.github/ci-config.env`](.github/ci-config.env)). They run on **`workflow_dispatch`**, and CPU BFB callers also run on push to **`hackathon-*`**, **`hackathon`**, **`hackathon/**`**, or legacy **`feature-ci-bfb`**. **GPU BFB** workflows (`bfb-io-gpu`, `bfb-decomp-gpu`) use NVHPC + CUDA + OpenACC, double precision, CIRRUS runners, and only `workflow_dispatch` — same policy as the GPU ECT subset.

| Test | Status |
|------|--------|
| BFB: I/O (SMIOL vs PIO) | [![BFB: I/O (SMIOL vs PIO)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/bfb-io.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/bfb-io.yml) |
| BFB: Decomposition (1 vs 4 ranks) | [![BFB: Decomposition (1 vs 4 ranks)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/bfb-decomp.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/bfb-decomp.yml) |
| BFB: I/O GPU (SMIOL vs PIO) | [![BFB: I/O GPU (SMIOL vs PIO)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/bfb-io-gpu.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/bfb-io-gpu.yml) |
| BFB: Decomposition GPU (1 vs 4 ranks) | [![BFB: Decomposition GPU (1 vs 4 ranks)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/bfb-decomp-gpu.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/bfb-decomp-gpu.yml) |
| Code coverage | [![Code Coverage](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/coverage.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/coverage.yml) [![codecov](https://codecov.io/gh/NCAR/MPAS-Model-CI/graph/badge.svg)](https://codecov.io/gh/NCAR/MPAS-Model-CI) |

Container images are from [ncarcisl/hpcdev](https://hub.docker.com/r/ncarcisl/hpcdev-x86_64).
Image tags, compiler mappings, and MPI flags are configured in [`.github/ci-config.env`](.github/ci-config.env).

### Hackathon quick start

- Use **`master`** as the base branch. Shared CI settings and container tags are in [`.github/ci-config.env`](.github/ci-config.env); reusable workflows live under [`.github/workflows/`](.github/workflows/).
- **Fork → branch → PR** into [`NCAR/MPAS-Model-CI`](https://github.com/NCAR/MPAS-Model-CI) with base **`master`** (not the upstream `MPAS-Dev/MPAS-Model` fork unless that is intentional).
- **Test another MPAS fork or commit:** Actions → **Cross-Repo Test** or use **`workflow_dispatch`** on **Ensemble Consistency Test (ECT)**, **coverage**, or **ect-ensemble-gen** with `mpas-repository` / `mpas-ref`. Details: [`.github/docs/testing-upstream-commits.md`](.github/docs/testing-upstream-commits.md).
- **GPU ECT** (`test-gpu-mpich` / `test-gpu-openmpi`) is **`workflow_dispatch` only** (CIRRUS self-hosted — not tied to `hackathon-*` pushes). **GPU BFB** and **Nsight profiling** are also **manual dispatch**; coordinate with maintainers as needed.

The Model for Prediction Across Scales (MPAS) is a collaborative project for
developing atmosphere, ocean, and other earth-system simulation components for
use in climate, regional climate, and weather studies. The primary development
partners are the climate modeling group at Los Alamos National Laboratory
(COSIM) and the National Center for Atmospheric Research. Both primary
partners are responsible for the MPAS framework, operators, and tools common to
the applications; LANL has primary responsibility for the ocean model, and NCAR
has primary responsibility for the atmospheric model.

The MPAS framework facilitates the rapid development and prototyping of models
by providing infrastructure typically required by model developers, including
high-level data types, communication routines, and I/O routines. By using MPAS,
developers can leverage pre-existing code and focus more on development of
their model.

BUILDING
========

This README is provided as a brief introduction to the MPAS framework. It does
not provide details about each specific model, nor does it provide building
instructions.

For information about building and running each core, please refer to each
core's user's guide, which can be found at the following web sites:

[MPAS-Atmosphere](http://mpas-dev.github.io/atmosphere/atmosphere_download.html)

[MPAS-Albany Land Ice](http://mpas-dev.github.io/land_ice/download.html)

[MPAS-Ocean](http://mpas-dev.github.io/ocean/releases.html)

[MPAS-Seaice](http://mpas-dev.github.io/sea_ice/releases.html)


Code Layout
----------

Within the MPAS repository, code is laid out as follows. Sub-directories are
only described below the src directory.

	MPAS-Model
	├── src
	│   ├── driver -- Main driver for MPAS in stand-alone mode (Shared)
	│   ├── external -- External software for MPAS (Shared)
	│   ├── framework -- MPAS Framework (Includes DDT Descriptions, and shared routines. Shared)
	│   ├── operators -- MPAS Opeartors (Includes Operators for MPAS meshes. Shared)
	│   ├── tools -- Empty directory for include files that Registry generates (Shared)
	│   │   ├── registry -- Code for building Registry.xml parser (Shared)
	│   │   └── input_gen -- Code for generating streams and namelist files (Shared)
	│   └── core_* -- Individual model cores.
	│       └── inc -- Empty directory for include files that Registry generates
	├── testing_and_setup -- Tools for setting up configurations and test cases (Shared)
	└── default_inputs -- Copies of default stream and namelists files (Shared)

Model cores are typically developed independently. For information about
building and running a particular core, please refer to that core's user's
guide.
