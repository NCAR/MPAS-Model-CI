# ECT cases: how they work and how to change them

`.github/ect-cases.yml` defines what the Ensemble Consistency Test (ECT) runs. Read this before editing it.

## Why care

Each case is tied to a **reference ensemble**: a summary file and a spin-up restart, generated from that case and
stored as release assets in the ECT release for the MPAS series (`ect-v<MAJOR.MINOR>`, e.g. `ect-v8.4`, derived from
`src/core_atmosphere/Registry.xml`). A test run compares new model output against that ensemble. If you change what a
case runs (its data, namelist or ensemble settings) without regenerating its ensemble, every later test compares
against a reference made from something else, and its PASS/FAIL means nothing. Ask the CI maintainers before adding or
changing a case.

## Fields

```yaml
default: <case>              # used when a workflow's ect-case input is empty

data:                        # test-data archives, from https://github.com/NCAR/MPAS-Model-CI/releases
  <name>: {tag: <release tag>}           # the file <name>.tar.gz in that release (optional `asset:` gives another file name)

cases:
  <case>:
    description: <free text>
    data: [<name>]                       # entries from `data`, by name; the first is the base case directory
    ensemble:
      spinup: "<D_HH:MM:SS>"             # unperturbed spin-up before members are perturbed (quote it)
      run: "<D_HH:MM:SS>"                # length of each perturbed member (quote it)
      size: <n>                          # reference ensemble size (>= number of analysed variables, ~48 minimum)
      perturb: {variable: theta, magnitude: "1e-14"}   # initial-condition perturbation (double precision)
      excluded-vars: <path>              # file in the repo listing history variables PyCECT ignores
      boundary-mask: true                # limited-area cases only (optional, default false); see below
    assets:
      summary: <file>.nc                 # ensemble summary in the ECT release
      restart: <file>.nc                 # spin-up restart in the ECT release (stored as <file>.nc.gz)
```

Quote durations and magnitudes: YAML reads an unquoted `1_00:00:00` as a number. The resolver
(`.github/scripts/resolve-ect-case.py`) rejects unknown fields and missing values, and lists the valid case names when
a name is wrong.

**Asset names are set here, not by the workflows.** "ECT Ensemble Generation" publishes the summary and restart under
the names in `assets`, and test runs download them by the same names. Naming rule: summary
`mpas_ect_summary_<data>_<case>.nc`, restart `<data>-<case>-spinup-restart.nc`. Never give two cases the same names.

**External sources.** If a case recreates a case defined elsewhere, say where from (repository, commit, script) in a
comment above it. It is a comment on purpose: CI does not read or run it.

**Limited-area cases (`boundary-mask: true`).** In a limited-area run, the cells near the edge of the region (the
relaxation and specified zones, `bdyMaskCell` > 0) are driven by the lateral boundary conditions, which are the same in
every member, so they have almost no spread and dilute the means PyCECT compares (on the 120km CONUS region they are 44%
of the cells). With `boundary-mask: true`, the trimming step sets the area weights (`areaCell`, `dvEdge`,
`areaTriangle`) of those points to zero in the history files given to PyCECT, using the masks in the case's init file,
so the means cover the interior only. Ensemble generation and tests trim the same way. This relies on PyCECT taking its
weights from those variables (true for the pinned version); recheck it when `PYCECT_TAG` changes.

## Adding a case

1. **Data.** If the case needs files that are not listed under `data`, build a `.tar.gz`, publish it under a new
   release tag (`gh release create <tag> <name>.tar.gz --repo NCAR/MPAS-Model-CI`) and add `<name>: {tag: <tag>}`.
2. **Case.** Copy an existing case, give it a descriptive name and new asset names, and describe it.
3. **Reference ensemble.** Run "ECT Ensemble Generation" (Actions tab) with `ect-case` set to the new case. It builds
   the model, runs the spin-up and the ensemble, and publishes the case's summary and restart to the ECT release.
4. **Test it passes.** Run "Ensemble Consistency Test (ECT)" with the new case on an unchanged build: it must PASS.
5. **Test it can fail.** Run it on a build with a deliberate, small change to the science (a control): it must FAIL.
   A case that cannot fail tests nothing.
6. **PR.** Open the pull request with links to the runs from steps 3 to 5.

## Changing a case

Never edit a case in place to change what it runs. Make the change, give the case new asset names (e.g. add `_v2`),
and repeat steps 3 to 6. Editing only `description` or comments needs nothing else.

## Changing data

Never upload a different file under an existing release tag: CI runners cache archives by tag, so some runs would keep
the old file, and older commits pinned to that tag would change underneath. Publish a new tag (`-v2`, `-v3`, ...) and
update the entry. Old tags stay available; public-repository releases have no total-size limit (each file must be
under 2 GiB), so remove old versions only deliberately, once nothing reads them.

## Removing a case

Delete it from `ect-cases.yml`. Its release assets stay until the maintainers prune them.

## New MPAS series

A new minor version (e.g. 8.4 to 8.5) means a new ECT release, so every case needs step 3 again.

## Legacy asset names

Before cases existed, the default case used `mpas_ect_summary_120km.nc` and `120km-spinup-restart.nc.gz`. Those files
stay on the existing ECT releases, frozen at their 2026-10-17 versions, for forks that still read them. Nothing in this
repository reads or writes them.
