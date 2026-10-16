! Two ranks exchange a DEVICE buffer through MPI (OpenACC host_data use_device). If the MPI library is not CUDA-aware this
! crashes, hangs or returns wrong data; if it is, it prints PASS. Mirrors what MPAS does with config_gpu_aware_mpi = true.
program devsend
  use mpi
  implicit none
  integer, parameter :: n = 1048576
  integer :: ierr, rank, nprocs, i, st(MPI_STATUS_SIZE), partner
  double precision, allocatable :: a(:), b(:)
  double precision :: err
  call MPI_Init(ierr)
  call MPI_Comm_rank(MPI_COMM_WORLD, rank, ierr)
  call MPI_Comm_size(MPI_COMM_WORLD, nprocs, ierr)
  if (nprocs /= 2) then
     if (rank == 0) print *, 'run with exactly 2 ranks'
     call MPI_Abort(MPI_COMM_WORLD, 2, ierr)
  end if
  partner = 1 - rank
  allocate(a(n), b(n))
  !$acc enter data create(a, b)
  !$acc parallel loop present(a, b)
  do i = 1, n
     a(i) = dble(i) * dble(rank + 1)
     b(i) = -1.0d0
  end do
  !$acc host_data use_device(a, b)
  call MPI_Sendrecv(a, n, MPI_DOUBLE_PRECISION, partner, 7, b, n, MPI_DOUBLE_PRECISION, partner, 7, MPI_COMM_WORLD, st, ierr)
  !$acc end host_data
  err = 0.0d0
  !$acc parallel loop present(b) reduction(+:err)
  do i = 1, n
     err = err + abs(b(i) - dble(i) * dble(partner + 1))
  end do
  if (rank == 0) then
     if (ierr == 0 .and. err == 0.0d0) then
        print *, 'DEVSEND RESULT: PASS (device buffers exchanged correctly)'
     else
        print *, 'DEVSEND RESULT: FAIL err=', err, ' ierr=', ierr
     end if
  end if
  !$acc exit data delete(a, b)
  call MPI_Finalize(ierr)
end program devsend
