# SANE workflows for MPAS-A (prototype)

Port of the approach in `islas/WRF` (`.sane/wrf`, `sane_ci.yml`, `labeled_test.yml`) to MPAS-A.
SANE (https://sane-workflows.readthedocs.io) builds a DAG of actions and submits each one
to PBS on Derecho with the right modules and resources; GitHub Actions only launches it.

```
.sane/mpas
├── hosts/derecho.jsonc       # PBS host: queues, account, test data paths (config.mpas.*)
├── hosts/derecho_envs.jsonc  # gnu / intel-oneapi / nvhpc module sets + per-action resources
├── scripts/                  # build_mpas.sh, run_mpas.sh, compare_bfb.sh (do the real work)
└── tests/mpas.py             # generates actions
```

## Actions
| Action | What |
|---|---|
| `build_mpas_<gnu\|intel-oneapi\|nvhpc>_<double\|single>` | out-of-tree CPU build, outputs `executable` |
| `testdata_120km` | local (login node): uses/downloads the 120km case |
| `bfb_decomp_gnu_r4`, `_r36` | 1 h run of the gnu/double build at 4 and 36 ranks |
| `bfb_decomp_gnu` | local: `cmp`, then `.github/scripts/compare-bfb-nc.py`, 4 vs 36 ranks |

## Run it
```bash
python3 -m venv venv-sane && venv-sane/bin/pip install --pre sane-workflows
venv-sane/bin/sane workflow -p .sane -sh derecho -l -vg -a bfb_decomp_gnu            # graph
venv-sane/bin/sane workflow -p .sane -sh derecho -d -n -v -a bfb_decomp_gnu \
    -sl ~/sane_state -ll ~/sane_logs                                                # PBS dry-run
venv-sane/bin/sane workflow -p .sane -sh derecho -r -a bfb_decomp_gnu \
    -sl ~/sane_state -ll ~/sane_logs                                                # real
```
Keep `-sl`/`-ll` outside `.sane/` (it scans recursively). Reuse of saved state skips finished
actions; pass `-n` for a fresh run.

## Site settings to review
* `account` and `config.mpas.*` in `hosts/derecho.jsonc` (account NTDD0004 and the test-data
  and Python paths are the author's; override with a host patch via `-p`).
* `config.mpas.python` needs `netCDF4` + `numpy` (only used if `cmp` reports a difference).
* Not carried over from the GitHub CI containers: `MPAS_MPI_F08=0`, `-tp=px`.

## Not done yet
ECT test, GPU/OpenACC builds, OpenMP variants, io/PIO variants, known-failure filtering,
commit-status reporting and label triggers (see WRF `labeled_test.yml`).
