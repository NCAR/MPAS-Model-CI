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

## Supported Workflows

All five CI workflows support cross-repo testing via `workflow_dispatch` inputs:

| Workflow | File | Description |
|----------|------|-------------|
| (GitHub Actions) Build All, Run NoGPU | `test-ga-nogpu.yml` | Full compiler/MPI/IO matrix on GitHub runners |
| (CIRRUS) NVHPC GPU vs CPU | `test-cirrus-nvhpc.yml` | NVHPC builds on self-hosted GPU runners |
| Ensemble Consistency Test (ECT) | `ect-test.yml` | Quick 3-member ECT validation |
| ECT Ensemble Generation | `ect-ensemble-gen.yml` | Generate new ensemble summary (expensive) |
| Code Coverage | `coverage.yml` | GCC coverage build + Codecov upload |

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

## Using the GitHub CLI

You can also trigger workflows from the command line with `gh`:

```bash
# Test MPAS-Dev/MPAS-Model develop branch with the full test suite
gh workflow run test-ga-nogpu.yml \
  -R NCAR/MPAS-Model-CI \
  --ref feature-ci-test-cases \
  -f mpas-repository=MPAS-Dev/MPAS-Model \
  -f mpas-ref=develop

# Test a specific commit with ECT
gh workflow run ect-test.yml \
  -R NCAR/MPAS-Model-CI \
  --ref feature-ci-test-cases \
  -f mpas-repository=MPAS-Dev/MPAS-Model \
  -f mpas-ref=a1b2c3d4e5f67890abcdef1234567890abcdef12

# Run coverage on a tagged release
gh workflow run coverage.yml \
  -R NCAR/MPAS-Model-CI \
  --ref feature-ci-test-cases \
  -f mpas-repository=MPAS-Dev/MPAS-Model \
  -f mpas-ref=v8.3.0
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
