import itertools

import sane

# Make target for each host environment (see .sane/mpas/hosts/derecho_envs.jsonc)
ENV_TARGETS = { "gnu" : "gfortran", "intel-oneapi" : "intel", "nvhpc" : "nvhpc" }

SCRIPTS = ".sane/mpas/scripts"


@sane.register
def add_mpas_builds( orch ):
  """CPU builds of MPAS-A: build_mpas_<env>_<precision>"""
  orch.log( "Creating MPAS build permutations..." )
  for env, precision in itertools.product( ENV_TARGETS, [ "double", "single" ] ):
    action = sane.Action( f"build_mpas_{env}_{precision}" )
    action.config["command"]   = f"{SCRIPTS}/build_mpas.sh"
    action.config["build_dir"] = orch.working_directory + "/_build_${{ id }}"
    action.config["arguments"] = [ "-t", ENV_TARGETS[env], "-d", "${{ config.build_dir }}",
                                   "-p", precision, "-j", "${{ resources.cpus }}" ]
    action.outputs["executable"] = action.config["build_dir"] + "/atmosphere_model"
    action.add_resource_requirements( { "cpus" : 8 } )
    action.environment = env
    orch.add_action( action )


@sane.register
def add_testdata( orch ):
  """Make sure the 120km case exists, downloading it from the CI release if not.
  Runs on the login node (local) since compute nodes may not have internet access."""
  action = sane.Action( "testdata_120km" )
  action.local = True
  action.config["command"]   = "bash"
  action.config["arguments"] = [ "-c",
    'if [ -d "$1" ]; then echo "Using existing $1"; '
    'else mkdir -p "$1" && curl -sL --retry 5 "$2" | tar -xz --strip-components=1 -C "$1"; fi',
    "--", "${{ host_info.config.mpas.testdata_120km }}", "${{ host_info.config.mpas.testdata_120km_url }}" ]
  action.outputs["case_dir"] = "${{ host_info.config.mpas.testdata_120km }}"
  action.add_resource_requirements( { "cpus" : 1 } )
  action.environment = "gnu"
  orch.add_action( action )


@sane.register
def add_bfb_decomp( orch ):
  """BFB test: the same build run on different MPI decompositions must give identical history.

  Partition files for the 120km case exist for 4, 36 and 128 ranks; the first rank count
  is the reference. Actions: bfb_decomp_<env>_r<N> (runs) and bfb_decomp_<env> (compare).
  """
  ranks    = [ 4, 36 ]
  duration = "0_01:00:00"
  for env in [ "gnu" ]:
    build = f"build_mpas_{env}_double"
    runs  = []
    for n in ranks:
      run = sane.Action( f"bfb_decomp_{env}_r{n}" )
      run.config["run_dir"]   = orch.working_directory + "/bfb/${{ id }}"
      run.config["command"]   = f"{SCRIPTS}/run_mpas.sh"
      run.config["arguments"] = [ "-e", "${{ dependencies." + build + ".outputs.executable }}",
                                  "-c", "${{ dependencies.testdata_120km.outputs.case_dir }}",
                                  "-r", "${{ config.run_dir }}",
                                  "-n", "${{ resources.cpus }}",
                                  "-t", duration ]
      run.outputs["run_dir"] = run.config["run_dir"]
      run.add_dependencies( build, "testdata_120km" )
      run.add_resource_requirements( { "cpus" : n } )
      run.environment = env
      orch.add_action( run )
      runs.append( run )

    compare = sane.Action( f"bfb_decomp_{env}" )
    compare.local = True
    compare.config["command"]   = f"{SCRIPTS}/compare_bfb.sh"
    compare.config["arguments"] = [ "-c", ".github/scripts/compare-bfb-nc.py",
                                    "-p", "${{ host_info.config.mpas.python }}" ]
    compare.config["arguments"] += [ "${{ dependencies." + r.id + ".outputs.run_dir }}" for r in runs ]
    compare.add_dependencies( *[ r.id for r in runs ] )
    compare.add_resource_requirements( { "cpus" : 1 } )
    compare.environment = env
    orch.add_action( compare )
