find_package(PFUNIT REQUIRED)

# Spline interpolation tests
add_pfunit_ctest(test_spline_interpolation
  TEST_SOURCES test_spline_interpolation.pf
  LINK_LIBRARIES mpas_testable_procedures
)
target_compile_options(test_spline_interpolation
  PRIVATE
    $<$<Fortran_COMPILER_ID:GNU>:-fbacktrace -ffree-line-length-none>
    $<$<Fortran_COMPILER_ID:Intel>:-traceback>
    $<$<Fortran_COMPILER_ID:IntelLLVM>:-traceback>
)
