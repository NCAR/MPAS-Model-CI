# Source this (do not execute) to set the MPI-library environment for GPU-aware halos (device buffers handed to MPI).
# Requires MPI_IMPL (mpich|openmpi); MPI_FLAGS is left untouched. Pair with enable-gpu-aware-mpi.sh (namelist side).
#
# Verified in the CI GPU containers (almalinux9-nvhpc-{mpich,openmpi}-cuda-26.02) by the check-gpu-aware-mpi workflow:
#   mpich   4.3.2, ch4:ucx, --with-cuda: handles device buffers. GPU support is on by default; it is set explicitly below
#           (MPIR_CVAR_ENABLE_GPU is stock MPICH; MPICH_GPU_SUPPORT_ENABLED is Cray MPICH's variable, harmless here).
#   openmpi 5.0.9, --with-cuda (accelerator:cuda, btl:smcuda; there is NO ucx pml/osc component in the image): CUDA-aware on a
#           node by default. Forcing OMPI_MCA_pml=ucx / --mca pml ucx aborts MPI_Init ("Framework: pml, Component: ucx not
#           found"), so nothing is set for OpenMPI.
# If a container's MPI is not built with CUDA support, the run fails loudly (segfault/abort) instead of silently staging.
case "${MPI_IMPL}" in
  mpich)
    export MPIR_CVAR_ENABLE_GPU=1
    export MPICH_GPU_SUPPORT_ENABLED=1
    ;;
  openmpi)
    : # CUDA-aware by default; do not force UCX (see above)
    ;;
esac
