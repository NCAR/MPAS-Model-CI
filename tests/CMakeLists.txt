cmake_minimum_required(VERSION 3.21)

project(mpas_unit_tests
  VERSION 0.1.0
  DESCRIPTION "Unit tests for standalone MPAS-Model procedures"
  LANGUAGES Fortran
)

# Build a small library from MPAS source files that have testable,
# standalone procedures with minimal dependencies.
# Add source files here as more tests are developed.
set(MPAS_SRC ${CMAKE_CURRENT_SOURCE_DIR}/../src)

add_library(mpas_testable_procedures)
target_sources(mpas_testable_procedures
  PRIVATE
    ${MPAS_SRC}/framework/mpas_kind_types.F
    ${MPAS_SRC}/operators/mpas_spline_interpolation.F
)
target_include_directories(mpas_testable_procedures
  INTERFACE ${CMAKE_CURRENT_BINARY_DIR}
)

# MPAS .F files are free-form Fortran with C preprocessor directives.
# gfortran treats .F as fixed-form by default, so we must override.
target_compile_options(mpas_testable_procedures
  PRIVATE
    $<$<Fortran_COMPILER_ID:GNU>:-cpp -ffree-form -fbacktrace -ffree-line-length-none>
    $<$<Fortran_COMPILER_ID:Intel>:-fpp -free -traceback>
    $<$<Fortran_COMPILER_ID:IntelLLVM>:-fpp -free -traceback>
)

if(PROJECT_IS_TOP_LEVEL)
  include(CTest)
  enable_testing()
endif()

if(BUILD_TESTING)
  add_subdirectory(unit)
endif()
