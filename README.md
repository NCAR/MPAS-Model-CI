MPAS-v8.3.1
====

## CI Status

### ECT (PyCECT)

MPICH subsets run on every push and PR. OpenMPI and GPU subsets are available via manual dispatch.
Each test builds in double precision, runs 3 perturbed ensemble members (4 MPI ranks), and validates with [PyCECT](https://github.com/NCAR/PyCECT).

| Compiler | MPI | Target | Status | Container |
|----------|-----|--------|--------|-----------|
| GNU | MPICH | CPU | [![GNU+MPICH (CPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gcc-mpich.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gcc-mpich.yml) | `hpcdev:almalinux9-gcc14-mpich-26.02` |
| GNU | OpenMPI | CPU | [![GNU+OpenMPI (CPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gcc-openmpi.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gcc-openmpi.yml) | `hpcdev:almalinux9-gcc14-openmpi-26.02` |
| Intel | MPICH | CPU | [![Intel+MPICH (CPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-intel-mpich.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-intel-mpich.yml) | `hpcdev:leap-oneapi-mpich-25.09`\* |
| Intel | OpenMPI | CPU | [![Intel+OpenMPI (CPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-intel-openmpi.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-intel-openmpi.yml) | `hpcdev:leap-oneapi-openmpi-25.09`\* |
| NVHPC | MPICH | CPU | [![NVHPC+MPICH (CPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-nvhpc-mpich.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-nvhpc-mpich.yml) | `hpcdev:almalinux9-nvhpc-mpich-26.02` |
| NVHPC | OpenMPI | CPU | [![NVHPC+OpenMPI (CPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-nvhpc-openmpi.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-nvhpc-openmpi.yml) | `hpcdev:almalinux9-nvhpc-openmpi-26.02` |
| NVHPC | MPICH | GPU | [![NVHPC+MPICH (GPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gpu-mpich.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gpu-mpich.yml) | `hpcdev:almalinux9-nvhpc-mpich-cuda-26.02` |
| NVHPC | OpenMPI | GPU | [![NVHPC+OpenMPI (GPU)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gpu-openmpi.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/test-gpu-openmpi.yml) | `hpcdev:almalinux9-nvhpc-openmpi-cuda-26.02` |

\* Intel pinned to `hpcdev 25.09` (IFX 2025.2) to avoid an [IFX 2025.3 preprocessor regression](.github/ci-config.env).

ECT subset container images are from [ncarcisl/hpcdev](https://hub.docker.com/r/ncarcisl/hpcdev-x86_64).
Image tags, compiler mappings, and MPI flags are configured in [`.github/ci-config.env`](.github/ci-config.env).

### Bit-for-bit and coverage

Bit-for-bit workflows compare history output in single precision (240km case; see `BFB_*` in [`.github/ci-config.env`](.github/ci-config.env)). They run on `workflow_dispatch` and on pushes to `feature-ci-bfb`.

| Test | Status |
|------|--------|
| BFB: I/O (SMIOL vs PIO) | [![BFB: I/O (SMIOL vs PIO)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/bfb-io.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/bfb-io.yml) |
| BFB: Decomposition (1 vs 4 ranks) | [![BFB: Decomposition (1 vs 4 ranks)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/bfb-decomp.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/bfb-decomp.yml) |
| Code coverage | [![Code Coverage](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/coverage.yml/badge.svg)](https://github.com/NCAR/MPAS-Model-CI/actions/workflows/coverage.yml) [![codecov](https://codecov.io/gh/NCAR/MPAS-Model-CI/graph/badge.svg)](https://codecov.io/gh/NCAR/MPAS-Model-CI) |

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
