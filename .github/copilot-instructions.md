# Copilot Instructions for MPAS-Model

This file provides AI assistants (Copilot, Cursor, etc.) with MPAS-specific
coding standards. Follow these conventions when writing, reviewing, or
suggesting changes to code in this repository.

Full contributor's guide: https://contributors-mpas-a.readthedocs.io/en/latest/CONTRIBUTING/

## File Conventions

- Use `.F` extension (capital F) for free-form Fortran with C preprocessor directives
- Maximum line length: **132 characters**
- Use **3-space indentation** (MPAS convention — not 2, not 4)
- Use **single quotes** for Fortran string literals
- File names match module names: `mpas_sort.F` contains `module mpas_sort`

## Naming Conventions

- **Modules**: `mpas_` prefix (`module mpas_sort`)
- **Public subroutines/functions**: `mpas_` prefix (`subroutine mpas_mergesort`)
- **Local variables**: camelCase (`threadNum`, `errorFile`, `localCount`)
- **Module-level constants**: descriptive lowercase or UPPER_CASE
- **Dummy arguments**: descriptive lowercase, matching the calling convention in context

## Module Structure

Modules should use explicit visibility control:

```fortran
module mpas_example

   use mpas_kind_types
   use mpas_derived_types
   use mpas_log

   implicit none
   private
   public :: mpas_example_compute

   contains

   subroutine mpas_example_compute(domain, inputField, outputField, ierr)!{{{

      implicit none

      ! Arguments
      type (domain_type), intent(inout) :: domain       !< Input/Output: MPAS domain
      real (kind=RKIND), intent(in) :: inputField(:)    !< Input: Field to process
      real (kind=RKIND), intent(out) :: outputField(:)  !< Output: Processed result
      integer, intent(out) :: ierr                      !< Output: Error code

      ! Local variables
      integer :: i, nCells

      ! ... implementation ...

   end subroutine mpas_example_compute!}}}

end module mpas_example
```

Required elements:
- `implicit none` in the module AND in every subroutine/function
- `private` by default, with explicit `public ::` declarations
- Explicit `intent` on all arguments — no exceptions
- Inline argument documentation: `!< Input:`, `!< Output:`, `!< Input/Output:`
- Separate `! Arguments` and `! Local variables` comment sections
- Fold markers: `!{{{` after the signature, `!}}}` after `end subroutine`

## Documentation

Use doxygen-style `!>` blocks before each public routine:

```fortran
!***********************************************************************
!
!  routine mpas_example
!
!> \brief   One-line description
!> \author  Your Name
!> \date    MM/DD/YY
!> \details
!> Longer description of what this routine does, its algorithm,
!> and any important constraints or assumptions.
!
!-----------------------------------------------------------------------
```

Use banner comments (`!***...` and `!-------`) to visually separate routines.

## Preprocessor

MPAS uses C preprocessor directives extensively:

- **MPI guards**: `#ifdef _MPI` / `#endif` around all MPI calls
- **MPI module selection**: `#ifdef MPAS_USE_MPI_F08` selects `use mpi_f08` vs `use mpi`
- **The COMMA macro**: `#define COMMA ,` allows passing commas inside macro
  arguments. This is an established pattern — do not refactor or remove it.
- **Debug write macros**: `DMPAR_DEBUG_WRITE(M)`, `STREAM_DEBUG_WRITE(M)`, etc.
  expand to commented-out `mpas_log_write` calls. Toggle by editing the `#define`.

## Patterns to Follow

- Use `mpas_log_write()` for all runtime messages
- Use `mpas_dmpar_global_abort()` for fatal errors (handles MPI cleanup)
- Check `allocated()` before deallocating arrays
- Wrap MPI calls in `#ifdef _MPI` blocks
- Use `intent(inout)` for arrays modified in-place (not `intent(out)`, which
  may cause automatic deallocation of allocatable components)
- Use MPAS kind types: `RKIND` for reals, `StrKIND` for strings

## GPU Acceleration (OpenACC)

MPAS uses OpenACC for GPU offloading. When adding or modifying GPU code:

```fortran
!$acc parallel loop
do iCell = 1, nCells
   ! computation
end do
!$acc end parallel loop
```

- Use `!$acc enter data copyin(...)` / `!$acc exit data copyout(...)` for
  data management
- GPU results are NOT expected to be bit-for-bit identical to CPU — use the
  Ensemble Consistency Test (ECT/PyCECT) to validate statistical equivalence
- Guard GPU-specific code with `#ifdef MPAS_OPENACC` when needed
- Always include a CPU fallback path
- Test with both `nogpu` and `cuda` builds

## Patterns to Avoid

- **No** `implicit none (external)` — Fortran 2018 feature not supported by all
  target compilers (GCC, NVHPC, Intel OneAPI)
- **No** `error stop` — use `mpas_dmpar_global_abort` instead
- **No** `write(*,*)` or `print *` — use `mpas_log_write`
- **No** Fortran 2018+ features (coarrays, `do concurrent` with reduction)
- **No** force-pushing to develop or master
- **No** large binary files committed to the repo — test data goes in
  `NCAR/mpas-ci-data`
- **Do not modify** code under `src/external/` (third-party vendored code)
- **Do not modify** code under `src/core_atmosphere/physics/physics_wrf/`
  (imported from WRF, follows WRF conventions)
- **Do not** submit unrelated formatting changes alongside functional changes
- Avoid trailing whitespace
- Avoid tabs (3-space indent only)

## Commit Messages

The first 80 characters are critical — they appear in `git log --oneline` and
must be greppable. Include the affected module/variable names and compiler if
relevant.

```
Fix memory leak in mpas_atm_core temperature deallocation (gfortran-11.3.0)

The temperature array in mpas_atm_core was not being properly deallocated
in the cleanup routine. Discovered during 72-hour CONUS_12km simulations.

Debugging process:
1. Used valgrind to identify the leak location
2. Root cause: double deallocation due to shared pointer logic
3. Solution: Added allocated() check before deallocation

Performance impact: Eliminated 2GB/hour memory leak
```

## Branch Naming

- Features: `feature/your-feature-name`
- Bug fixes: `bugfix/describe-the-bug`
- Always branch from `develop`, not `master`

## Code Review Checklist

When reviewing Fortran changes in MPAS, verify:

1. All new subroutines have `implicit none`
2. All arguments have explicit `intent`
3. New public names use `mpas_` prefix
4. Modules use `private` with explicit `public ::` declarations
5. Lines do not exceed 132 characters
6. Doxygen-style documentation block on new public routines
7. MPI calls are inside `#ifdef _MPI` guards
8. No raw `write(*,*)` — use `mpas_log_write`
9. Allocated arrays are properly deallocated on error paths
10. Changes preserve the `COMMA` macro pattern (don't "simplify" it)
11. No modifications to `src/external/` or WRF physics directories
12. New variables use camelCase; new public API uses `mpas_` prefix
13. Fold markers (`!{{{` / `!}}}`) on new subroutines
14. GPU code validated via ECT (not bit-for-bit — statistical equivalence)
15. Commit message first line ≤ 80 chars with module/variable names
