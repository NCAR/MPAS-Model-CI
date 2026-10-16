# Source this (do not execute) to set the MPI-library GPU-support environment for GPU-aware halos.
# Requires MPI_IMPL (mpich|openmpi) and MPI_FLAGS to be set; appends to MPI_FLAGS for OpenMPI.
# Needs the container's MPI to be built with CUDA support; if it is not, MPI aborts (loud) or falls back to
# host staging. Pair with enable-gpu-aware-mpi.sh (namelist side).
case "${MPI_IMPL}" in
  mpich)
    export MPICH_GPU_SUPPORT_ENABLED=1
    ;;
  openmpi)
    export OMPI_MCA_pml=ucx
    export OMPI_MCA_osc=ucx
    export UCX_TLS=cuda,cuda_copy,cuda_ipc,sm,self
    MPI_FLAGS="${MPI_FLAGS} --mca pml ucx --mca osc ucx"
    ;;
esac
