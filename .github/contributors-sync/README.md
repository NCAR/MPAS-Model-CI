# Contributors Guide — CI/CD Docs Sync

This directory contains the tooling to auto-generate the CI/CD page of the
[MPAS-A Contributors Guide](https://contributors-mpas-a.readthedocs.io/).

The generator script parses the actual workflow YAML, composite action
definitions, and test-case configs in this repo to produce an accurate
`ci-cd.md` page. A scheduled GitHub Actions workflow in the contributors
repo runs it weekly.

## Files

| File | Lives in | Purpose |
|------|----------|---------|
| `generate_ci_docs.py` | Both repos | Parses `.github/` and generates `docs/ci-cd.md` |
| `sync-docs.yml` | `NCAR/contributors-MPAS-A` | Scheduled workflow that runs the generator |
| `README.md` | `NCAR/MPAS-Model-CI` | This file (deployment instructions) |

## Deployment to NCAR/contributors-MPAS-A

### 1. Copy the workflow file

```bash
# Clone the contributors repo
git clone https://github.com/NCAR/contributors-MPAS-A.git
cd contributors-MPAS-A

# Copy the sync workflow
cp /path/to/MPAS-Model-CI/.github/contributors-sync/sync-docs.yml \
   .github/workflows/sync-docs.yml
```

### 2. Commit and push

```bash
git add .github/workflows/sync-docs.yml
git commit -m "Add scheduled CI/CD docs sync from MPAS-Model-CI"
git push
```

### 3. Run it manually to verify

```bash
gh workflow run sync-docs.yml -R NCAR/contributors-MPAS-A
```

The workflow will:
1. Checkout `contributors-MPAS-A`
2. Checkout `NCAR/MPAS-Model-CI` (sparse, `.github/` only)
3. Run `generate_ci_docs.py` to produce `docs/ci-cd.md`
4. Commit and push if anything changed

### 4. Verify on Read the Docs

After the commit lands, Read the Docs will auto-build. Check
https://contributors-mpas-a.readthedocs.io/en/latest/ci-cd/ for the
updated page.

## How it stays in sync

- The generator reads actual YAML files, not prose — it cannot go stale
  as long as the workflow files exist.
- The cron schedule runs every Monday at 06:00 UTC.
- Manual triggers via `workflow_dispatch` let you sync on demand.
- The `ci-branch` input defaults to `feature-ci-test-cases` — change this
  when the CI work moves to a different branch (e.g., `develop` or `master`).

## Running locally

```bash
cd /path/to/MPAS-Model-CI
python3 .github/contributors-sync/generate_ci_docs.py . -o /tmp/ci-cd.md
```

## Updating the generator

The generator script lives in this repo (`NCAR/MPAS-Model-CI`). The sync
workflow in `contributors-MPAS-A` always pulls the latest version from the
configured branch, so edits here take effect on the next sync run
automatically.
