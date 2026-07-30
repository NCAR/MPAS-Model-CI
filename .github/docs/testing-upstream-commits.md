# Testing Upstream MPAS-Model Commits

This guide explains how to run the CI workflows in `NCAR/MPAS-Model-CI` against
specific commits, branches, or tags in the upstream `MPAS-Dev/MPAS-Model`
repository.

## Overview

The CI infrastructure (workflows, composite actions, test case configs) lives in
`NCAR/MPAS-Model-CI`. The MPAS source code to be tested can come from any public
MPAS-Model fork. When you specify an external repository, the build jobs check
out that repo's source code and overlay the CI actions from `MPAS-Model-CI` so
the build/run/validate pipeline works unchanged.

Upstream feature work lands on **`develop`** (PRs against `MPAS-Dev/MPAS-Model`
`develop`); `master` is the release line. When validating a contributor PR in
this CI fork, prefer a **`PRtest-*`** branch based on **`develop`** (not
`master`) — see below.

## Supported Workflows

These workflows accept **`mpas-repository`** and **`mpas-ref`** (or require them) on **`workflow_dispatch`**:

| Workflow (Actions UI name) | File | Notes |
|-----------------------------|------|--------|
| Cross-Repo Test | `test-cross-repo.yml` | CPU compiler matrix (GCC, NVHPC, OneAPI) against an external repo/ref. Primary entry point for multi-compiler upstream checks. |
| Ensemble Consistency Test (ECT) | `ect-test.yml` | 3-member ECT on GitHub-hosted runners; optional cross-repo inputs. |
| ECT Ensemble Generation | `ect-ensemble-gen.yml` | Expensive ensemble summary generation; optional cross-repo inputs. |
| Code Coverage | `coverage.yml` | GCC coverage + Codecov; optional cross-repo inputs. |

Per-compiler subset workflows (e.g. `test-gcc-mpich.yml`) do **not** expose cross-repo inputs on their own; use **Cross-Repo Test** or call `_test-compiler.yml` from a wrapper that passes `mpas-repository` / `mpas-ref`.

**GPU** ECT (`_test-gpu.yml`) does **not** support external repo checkout until the cross-repo inputs on CIRRUS are re-enabled (see comments in `_test-gpu.yml`).

## How to Trigger

1. Go to the **Actions** tab of `NCAR/MPAS-Model-CI`
2. Select the workflow you want to run
3. Click **Run workflow**
4. Fill in the inputs:
   - **mpas-repository**: The `owner/repo` of the MPAS source (e.g. `MPAS-Dev/MPAS-Model`)
   - **mpas-ref**: A branch name, tag, or full commit SHA from that repo
5. Click **Run workflow**

### Input Details

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `mpas-repository` | No | *(empty — uses MPAS-Model-CI itself)* | GitHub repository in `owner/repo` format |
| `mpas-ref` | No | *(empty — default branch)* | Any valid git ref: branch name, tag, or 40-character SHA |

### Examples

**Test the latest `develop` branch of MPAS-Model:**
- mpas-repository: `MPAS-Dev/MPAS-Model`
- mpas-ref: `develop`

**Test a specific commit:**
- mpas-repository: `MPAS-Dev/MPAS-Model`
- mpas-ref: `a1b2c3d4e5f6...` (full 40-char SHA)

**Test a tagged release:**
- mpas-repository: `MPAS-Dev/MPAS-Model`
- mpas-ref: `v8.3.0`

**Test a fork (e.g. a contributor's branch):**
- mpas-repository: `username/MPAS-Model`
- mpas-ref: `feature-branch`

**Default behavior (test MPAS-Model-CI itself):**
- Leave both fields empty

## Testing a PR on a `PRtest-*` branch (preferred for develop-based PRs)

Contributor PRs target upstream **`develop`**. To run the full CPU compiler /
ECT / BFB push CI against such a PR inside this fork:

1. Branch from **`origin/develop`** (science integration tip).
2. Overlay CI from **`origin/master`** (`.github/`, and `tests/` if needed).
3. Cherry-pick the PR commit(s) on top.
4. Push as **`PRtest-<short-name>`** (e.g. `PRtest-incomplete-gamma-fixes`).

Branches matching `PRtest-*` auto-trigger the same MPICH CPU subsets, CUDA
compile-only, and BFB callers as `hackathon-*`. Use `PRtest-*` for PR
validation; keep `hackathon-*` for hackathon experiments.

Example:

```bash
git fetch origin develop master
git checkout -B PRtest-my-pr origin/develop
git checkout origin/master -- .github tests
git add .github tests
git commit -m "ci: overlay CI infrastructure for PRtest"

# Cherry-pick PR commits (from the contributor fork or pull/<n>/head)
git fetch https://github.com/MPAS-Dev/MPAS-Model.git pull/1486/head
git cherry-pick <sha>...

git push -u origin PRtest-my-pr
```

Alternatively, use **Cross-Repo Test** `workflow_dispatch` with
`mpas-repository` / `mpas-ref` pointing at the contributor fork (no local
branch required).

## Using the GitHub CLI

You can also trigger workflows from the command line with `gh`:

```bash
# CPU matrix (GCC + NVHPC + OneAPI) against MPAS-Dev develop
gh workflow run test-cross-repo.yml \
  -R NCAR/MPAS-Model-CI \
  --ref master \
  -f mpas-repository=MPAS-Dev/MPAS-Model \
  -f mpas-ref=develop

# ECT against a specific commit (empty mpas-repository = this repo)
gh workflow run ect-test.yml \
  -R NCAR/MPAS-Model-CI \
  --ref master \
  -f mpas-repository=MPAS-Dev/MPAS-Model \
  -f mpas-ref=a1b2c3d4e5f67890abcdef1234567890abcdef12

# Coverage on a tagged release
gh workflow run coverage.yml \
  -R NCAR/MPAS-Model-CI \
  --ref master \
  -f mpas-repository=MPAS-Dev/MPAS-Model \
  -f mpas-ref=v8.4.0
```

Note: `--ref` specifies which branch of **MPAS-Model-CI** to use for the
workflow definition (i.e., which version of the CI infrastructure). The `-f`
flags specify which **MPAS source code** to build.

## How It Works

```
┌─────────────────────────────────────────────────────┐
│  Build Job                                          │
│                                                     │
│  1. Checkout MPAS source (target repo + submodules) │
│  2. Overlay .github/ from MPAS-Model-CI             │
│  3. Build with .github/actions/build-mpas           │
│  4. Upload executable as artifact                   │
└──────────────────────┬──────────────────────────────┘
                       │ artifact: atmosphere_model
┌──────────────────────▼──────────────────────────────┐
│  Run / ECT-Run Jobs                                 │
│                                                     │
│  1. Checkout MPAS-Model-CI (for composite actions)  │
│  2. Download executable artifact                    │
│  3. Run MPAS-A                                      │
└──────────────────────┬──────────────────────────────┘
                       │ artifact: logs / history files
┌──────────────────────▼──────────────────────────────┐
│  Validate / ECT-Validate / Summary Jobs             │
│                                                     │
│  1. Checkout .github/ from MPAS-Model-CI            │
│  2. Download result artifacts                       │
│  3. Validate and report                             │
└─────────────────────────────────────────────────────┘
```

Only the build job checks out the target MPAS repository. All subsequent jobs
use the compiled executable (passed as an artifact) and CI infrastructure from
MPAS-Model-CI.

## Requirements

- The target repository must be **publicly accessible**. Private repositories
  require a Personal Access Token (PAT) configured as a repository secret, which
  is not currently set up.
- The target repository must have the standard MPAS-Model directory structure
  (`src/`, `Makefile`, submodules for `MPAS-Tools` and `MPAS-Data`).

## Interpreting Results

CI results appear in the Actions tab of `NCAR/MPAS-Model-CI`. Each run shows:

- **Run title**: The workflow name
- **Triggered by**: The user who dispatched it
- **Branch**: The MPAS-Model-CI branch (determines which CI version ran)

To see which MPAS source was tested, click into the run and check the build
job's "Checkout MPAS source" step — it logs the repository and ref that were
checked out.

The validation results (log comparison, ECT pass/fail) apply to the MPAS source
code at the specified ref, built and run using the CI infrastructure from
MPAS-Model-CI.
