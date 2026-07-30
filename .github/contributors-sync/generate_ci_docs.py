#!/usr/bin/env python3
"""Generate the CI/CD documentation page for the MPAS-A Contributors Guide.

Parses the actual workflow YAML files, composite action definitions, and
test-case configs from the NCAR/MPAS-Model-CI repository to produce an
accurate, contributor-focused ci-cd.md page.

The output is structured for an atmospheric scientist or student audience:
it leads with *what* the CI checks and *why*, not *how* the YAML works.

Usage:
    python generate_ci_docs.py <mpas-model-ci-path> -o docs/ci-cd.md
"""

import argparse
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import yaml


# ── helpers ──────────────────────────────────────────────────────────────

def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def load_env(path):
    """Parse a shell config.env file into a dict."""
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def fmt_list(items):
    return ", ".join(f"`{x}`" for x in items)


def extract_matrix(job):
    return job.get("strategy", {}).get("matrix", {})


def extract_container(job):
    c = job.get("container", {})
    return c if isinstance(c, str) else c.get("image", "")


def resolve_matrix_dims(matrix):
    """Return only the list-valued dimensions (the cartesian axes)."""
    return {k: v for k, v in matrix.items() if isinstance(v, list)}


# Friendly display names for raw matrix values
COMPILER_NAMES = {"gcc": "GCC (gfortran)", "nvhpc": "NVHPC (nvfortran)", "oneapi": "Intel OneAPI (ifx)"}
MPI_NAMES = {"mpich3": "MPICH 3", "mpich": "MPICH 4", "openmpi": "OpenMPI"}
IO_NAMES = {"smiol": "SMIOL", "pio": "PIO"}
GPU_NAMES = {"nogpu": "CPU-only", "cuda": "GPU (CUDA/OpenACC)"}


def friendly(value, lookup):
    return lookup.get(value, value)


def friendly_list(values, lookup):
    return ", ".join(friendly(v, lookup) for v in values)


# ── workflow grouping ────────────────────────────────────────────────────

WORKFLOW_GROUPS = {
    "Main testing": ["test-ga-nogpu", "test-cirrus-nvhpc"],
    "Ensemble Consistency Test": ["ect-test", "ect-ensemble-gen"],
    "Code quality": ["coverage"],
}


def group_workflows(workflows_dir):
    """Return workflows grouped by purpose, with an 'Other' catch-all."""
    by_stem = {}
    for p in sorted(workflows_dir.glob("*.yml")):
        wf = load_yaml(p)
        if wf:
            by_stem[p.stem] = (p, wf)

    grouped = {}
    seen = set()
    for group_name, stems in WORKFLOW_GROUPS.items():
        items = []
        for s in stems:
            if s in by_stem:
                items.append(by_stem[s])
                seen.add(s)
        if items:
            grouped[group_name] = items

    other = [(p, wf) for s, (p, wf) in by_stem.items() if s not in seen]
    if other:
        grouped["Other"] = other

    return grouped


# ── section generators ───────────────────────────────────────────────────

def section_header(now):
    return textwrap.dedent(f"""\
        # MPAS-A CI/CD System

        !!! info "Auto-generated"
            This page is generated from the workflow files in
            [NCAR/MPAS-Model-CI](https://github.com/NCAR/MPAS-Model-CI).
            Last synced: {now}.
    """)


def section_what_ci_checks(ci_path):
    """Lead section: plain-language description of what CI does."""
    lines = [textwrap.dedent("""\
        ## What CI checks run on your code

        Every time code is pushed or a workflow is triggered manually, the CI
        system automatically:

        1. **Builds** MPAS-Atmosphere with multiple compilers and MPI libraries
        2. **Runs** the model on a standard test mesh at 1-process and 4-process
           decompositions
        3. **Validates** that the output logs match expected reference values
        4. **Runs an Ensemble Consistency Test (ECT)** to verify that your changes
           have not altered the model's scientific output beyond natural internal
           variability

        If all four stages pass, your code change is confirmed to be compatible
        with the existing model behavior.
    """)]

    lines.append(textwrap.dedent("""\
        ```mermaid
        graph LR
            B[Build MPAS-A] -->|executable| R[Run test case]
            B -->|executable| E[Run ECT members]
            R -->|log files| V[Validate logs]
            E -->|history files| ECT[ECT validation]
            ECT --> S[ECT summary table]
            V --> C[Cleanup]
            S --> C
        ```
    """))

    return "\n".join(lines)


def section_what_gets_tested(ci_path):
    """Resolve matrix values into a human-readable build matrix description."""
    wf_path = ci_path / ".github" / "workflows" / "test-ga-nogpu.yml"
    if not wf_path.exists():
        return ""

    wf = load_yaml(wf_path)
    build_job = (wf.get("jobs") or {}).get("build", {})
    matrix = resolve_matrix_dims(extract_matrix(build_job))

    compilers = matrix.get("compiler", [])
    mpis = matrix.get("mpi", [])
    ios = matrix.get("io", [])

    total = len(compilers) * len(mpis) * len(ios)

    lines = [textwrap.dedent("""\
        ## What gets tested

        The main CI workflow (`test-ga-nogpu.yml`) builds and runs MPAS-A across
        a matrix of compiler, MPI, and I/O combinations on GitHub-hosted runners:
    """)]

    lines.append("| Dimension | Options | Count |")
    lines.append("|-----------|---------|-------|")
    lines.append(f"| **Compilers** | {friendly_list(compilers, COMPILER_NAMES)} | {len(compilers)} |")
    lines.append(f"| **MPI libraries** | {friendly_list(mpis, MPI_NAMES)} | {len(mpis)} |")
    lines.append(f"| **I/O layers** | {friendly_list(ios, IO_NAMES)} | {len(ios)} |")
    lines.append(f"\nThis produces **{total} build configurations**. Each is then run at "
                 "**1 process** and **4 processes**, giving **{} total test runs**.\n".format(total * 2))

    # CIRRUS matrix
    cirrus_path = ci_path / ".github" / "workflows" / "test-cirrus-nvhpc.yml"
    if cirrus_path.exists():
        cwf = load_yaml(cirrus_path)
        cbuild = (cwf.get("jobs") or {}).get("build", {})
        cmatrix = resolve_matrix_dims(extract_matrix(cbuild))
        gpus = cmatrix.get("gpu", [])
        cmpis = cmatrix.get("mpi", [])
        cios = cmatrix.get("io", [])
        ctotal = len(gpus) * len(cmpis) * len(cios)

        lines.append(textwrap.dedent("""\
            A second workflow (`test-cirrus-nvhpc.yml`) runs on NCAR CIRRUS
            self-hosted runners with access to NVIDIA GPUs:
        """))
        lines.append("| Dimension | Options | Count |")
        lines.append("|-----------|---------|-------|")
        lines.append(f"| **GPU modes** | {friendly_list(gpus, GPU_NAMES)} | {len(gpus)} |")
        lines.append(f"| **MPI libraries** | {friendly_list(cmpis, MPI_NAMES)} | {len(cmpis)} |")
        lines.append(f"| **I/O layers** | {friendly_list(cios, IO_NAMES)} | {len(cios)} |")
        lines.append(f"\nThis produces **{ctotal} NVHPC configurations** testing both CPU "
                     "and GPU (OpenACC/CUDA) code paths.\n")

    return "\n".join(lines)


def section_ect(ci_path):
    """Science-first ECT description."""
    config_path = ci_path / ".github" / "test-cases" / "ect-120km" / "config.env"
    env = load_env(config_path) if config_path.exists() else {}

    ensemble_size = env.get("ECT_ENSEMBLE_SIZE", "200")
    test_runs = env.get("ECT_TEST_RUNS", "3")
    magnitude = env.get("ECT_PERTURB_MAGNITUDE", "1e-14")
    variable = env.get("ECT_PERTURB_VARIABLE", "theta")
    duration = env.get("RUN_DURATION", "0_06:00:00")
    pycect_tag = env.get("PYCECT_TAG", "latest")

    hours = "6"
    if "_" in duration:
        _, time_part = duration.split("_", 1)
        hours = str(int(time_part.split(":")[0]))

    lines = [textwrap.dedent(f"""\
        ## Ensemble Consistency Test (ECT)

        The ECT detects whether a code change has altered the model's scientific
        output beyond what is expected from natural internal variability. It does
        **not** require bit-for-bit reproducibility — changes that are
        scientifically equivalent (e.g., optimization, refactoring) will pass.

        !!! tip "When to use ECT"
            Run ECT on code changes that are **not expected to change the science**
            (refactoring, performance work, build-system changes). A FAILED result
            means your change may have introduced an unintended scientific impact.

        **Reference:** Price-Broncucia et al. (2025),
        [doi:10.5194/gmd-18-2349-2025](https://doi.org/10.5194/gmd-18-2349-2025)

        ### How it works

        1. A **{ensemble_size}-member ensemble** is generated once (using
           `ect-ensemble-gen.yml`) by applying O({magnitude}) perturbations to the
           `{variable}` field in the initial conditions, then running {hours}-hour
           forecasts on a 120 km mesh
        2. The ensemble statistics are stored as a **summary file** in
           [`NCAR/mpas-ci-data`](https://github.com/NCAR/mpas-ci-data)
        3. When CI runs, **{test_runs} perturbed members** are generated for the
           code under test and compared against the summary using
           [PyCECT](https://github.com/NCAR/PyCECT) (pinned to tag `{pycect_tag}`)

        The ensemble summary only needs to be regenerated when there are major
        model version changes or intentional science modifications.

        ### ECT in the main CI workflows

        ECT validation runs for **every compiler/MPI/I/O combination** in both
        `test-ga-nogpu.yml` and `test-cirrus-nvhpc.yml`. Results from all
        combinations are collected into a single summary table at the bottom of
        the workflow run, so you can see at a glance which configurations passed.
    """)]

    return "\n".join(lines)


def section_reading_results():
    """New section: how to interpret CI results in the GitHub UI."""
    return textwrap.dedent("""\
        ## How to read CI results

        ### Finding results

        1. Go to the **Actions** tab in the GitHub repository
        2. Click on the workflow run you want to inspect
        3. Each colored dot represents a job — green means passed, red means
           failed, grey means skipped or cancelled

        ### What the results mean

        | Result | Meaning |
        |--------|---------|
        | **PASSED** | Model output is consistent with the reference ensemble |
        | **FAILED** | Output has changed beyond internal variability — investigate |
        | **SKIPPED** | Ensemble summary file not yet available (expected for new setups) |
        | **ERROR** | PyCECT or the model run crashed — check the job log |

        ### Re-running a workflow

        Click **Re-run all jobs** in the top-right corner of a workflow run page.
        For individual failures, expand the failed job and click **Re-run this job**.

        !!! note "Transient failures"
            Occasional failures from network timeouts or container issues are
            not related to your code. Re-running usually resolves them.
    """)


def section_cross_repo():
    """Cross-repo testing, condensed."""
    return textwrap.dedent("""\
        ## Testing specific MPAS-Model commits

        All workflows support building and testing MPAS source code from a
        different repository (e.g., `MPAS-Dev/MPAS-Model`) via the manual
        **Run workflow** button in the Actions tab. Two inputs are available:

        | Input | Description |
        |-------|-------------|
        | `mpas-repository` | The `owner/repo` to build (e.g., `MPAS-Dev/MPAS-Model`) |
        | `mpas-ref` | A branch name, tag, or commit SHA to check out |

        When set, the workflow checks out the MPAS source from the target
        repository and overlays the CI infrastructure from MPAS-Model-CI so all
        test actions work correctly.

        **Example using the GitHub CLI:**

        ```bash
        gh workflow run "test-ga-nogpu.yml" \\
          -f mpas-repository="MPAS-Dev/MPAS-Model" \\
          -f mpas-ref="develop"
        ```

        Leave both inputs empty to test the code in the current repository
        (the default behavior for push-triggered runs).
    """)


def section_reference(ci_path):
    """Collapsible developer reference: actions, containers, configs, MPI."""
    workflows_dir = ci_path / ".github" / "workflows"
    actions_dir = ci_path / ".github" / "actions"
    test_cases_dir = ci_path / ".github" / "test-cases"

    lines = [textwrap.dedent("""\
        ## CI Developer Reference

        ??? abstract "Expand for detailed reference on composite actions, containers, and configuration"
    """)]

    # ── Workflow inventory ───────────────────────────────────────────
    lines.append("    ### Workflows\n")

    grouped = group_workflows(workflows_dir)
    for group_name, items in grouped.items():
        lines.append(f"    **{group_name}**\n")
        lines.append("    | Workflow file | Name | Triggers |")
        lines.append("    |--------------|------|----------|")
        for wf_path, wf_data in items:
            wf_name = wf_data.get("name", wf_path.stem)
            on = wf_data.get("on", wf_data.get(True, {}))
            if isinstance(on, dict):
                triggers = fmt_list(on.keys())
            elif isinstance(on, list):
                triggers = fmt_list(on)
            else:
                triggers = str(on)
            lines.append(f"    | `{wf_path.name}` | {wf_name} | {triggers} |")
        lines.append("")

    # ── Composite actions ────────────────────────────────────────────
    lines.append("    ### Composite Actions\n")
    lines.append("    Reusable logic lives in `.github/actions/<name>/action.yml`.\n")

    for action_yml in sorted(actions_dir.glob("*/action.yml")):
        data = load_yaml(action_yml)
        name = data.get("name", action_yml.parent.name)
        desc = data.get("description", "")
        inputs = data.get("inputs", {})

        lines.append(f"    #### {name}\n")
        if desc:
            for desc_line in textwrap.wrap(desc.strip(), width=76):
                lines.append(f"    {desc_line}")
            lines.append("")
        lines.append(f"    **Directory:** `.github/actions/{action_yml.parent.name}/`\n")

        if inputs:
            lines.append("    | Input | Required | Default | Description |")
            lines.append("    |-------|----------|---------|-------------|")
            for iname, idef in inputs.items():
                req = "Yes" if idef.get("required", False) else "No"
                default = idef.get("default", "")
                idesc = idef.get("description", "")
                lines.append(f"    | `{iname}` | {req} | `{default}` | {idesc} |")
            lines.append("")

    # ── Container environment ────────────────────────────────────────
    lines.append("    ### Container Images\n")
    lines.append("    Builds and runs use NCAR CISL containers from "
                 "[Docker Hub](https://hub.docker.com/u/ncarcisl). Each container "
                 "ships with a specific compiler, MPI library, and pre-built I/O "
                 "libraries.\n")

    container_patterns = set()
    for wf_path in sorted(workflows_dir.glob("*.yml")):
        wf = load_yaml(wf_path)
        for job_def in (wf.get("jobs") or {}).values():
            if isinstance(job_def, dict):
                img = extract_container(job_def)
                if img and "${{" not in img:
                    container_patterns.add(img)

    if container_patterns:
        lines.append("    **Resolved container images:**\n")
        lines.append("    ```")
        for p in sorted(container_patterns):
            lines.append(f"    {p}")
        lines.append("    ```\n")
    lines.append("    Image pattern: "
                 "`ncarcisl/cisldev-x86_64-almalinux9-{compiler}-{mpi}:devel`"
                 " (with optional `-cuda` suffix for GPU builds).\n")

    lines.append("    All containers require sourcing `/container/config_env.sh` "
                 "before building or running MPI executables.\n")

    # ── MPI notes ────────────────────────────────────────────────────
    lines.append("    ### MPI Implementation Notes\n")
    lines.append("    | Matrix value | MPI version | Flags |")
    lines.append("    |-------------|-------------|-------|")
    lines.append("    | `mpich3` | MPICH 3.x | (none) |")
    lines.append("    | `mpich` | MPICH 4.x | (none) |")
    lines.append("    | `openmpi` | OpenMPI | `--allow-run-as-root --oversubscribe` |")
    lines.append("")

    # ── Test case configs ────────────────────────────────────────────
    lines.append("    ### Test Case Configurations\n")
    for config_path in sorted(test_cases_dir.glob("*/config.env")):
        env = load_env(config_path)
        case_name = config_path.parent.name
        lines.append(f"    #### {case_name}\n")
        lines.append("    | Parameter | Value |")
        lines.append("    |-----------|-------|")
        for key, value in sorted(env.items()):
            lines.append(f"    | `{key}` | `{value}` |")
        lines.append("")

    return "\n".join(lines)


def section_troubleshooting():
    return textwrap.dedent("""\
        ## Troubleshooting

        ??? warning "Common CI issues and fixes"

            **OpenMPI "root user" errors**
            : OpenMPI refuses to run as root by default (which GitHub Actions
              containers require). The `run-mpas` action adds
              `--allow-run-as-root --oversubscribe` automatically.

            **Stack size errors (Intel Fortran)**
            : Run `ulimit -s unlimited` before execution. The `run-mpas` action
              does this automatically.

            **Download failures (`curl` exit code 18)**
            : Large file transfers from GitHub can drop. The `download-testdata`
              action uses `--retry 5 --retry-delay 5` and caches archives across
              workflow runs.

            **PIO not found**
            : Set `PIO_ROOT=/container/pio` and `USE_PIO2=true`. The `build-mpas`
              action handles this when `use-pio: true`.

            **gfortran non-zero exit codes**
            : gfortran-compiled MPAS may exit non-zero due to IEEE floating-point
              warnings, not actual crashes. The `run-mpas` action uses
              `strict-exit-check: 'false'` for this.
    """)


def section_resources():
    return textwrap.dedent("""\
        ## Related Resources

        - [NCAR/MPAS-Model-CI](https://github.com/NCAR/MPAS-Model-CI) — CI
          workflow source
        - [MPAS-Dev/MPAS-Model](https://github.com/MPAS-Dev/MPAS-Model) —
          upstream MPAS source
        - [NCAR/mpas-ci-data](https://github.com/NCAR/mpas-ci-data) — test
          archives and ensemble summaries
        - [PyCECT](https://github.com/NCAR/PyCECT) — Ensemble Consistency Test
          tool
        - [NCAR CISL Docker Hub](https://hub.docker.com/u/ncarcisl) — container
          images
        - [GitHub Actions docs](https://docs.github.com/en/actions)
    """)


# ── main generator ───────────────────────────────────────────────────────

def generate(ci_path, output_path):
    ci_path = Path(ci_path)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    sections = [
        section_header(now),
        section_what_ci_checks(ci_path),
        section_what_gets_tested(ci_path),
        section_ect(ci_path),
        section_reading_results(),
        section_cross_repo(),
        section_reference(ci_path),
        section_troubleshooting(),
        section_resources(),
    ]

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n---\n\n".join(s for s in sections if s))
    print(f"Generated {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate CI/CD docs from MPAS-Model-CI workflow files"
    )
    parser.add_argument(
        "ci_repo_path",
        help="Path to local NCAR/MPAS-Model-CI checkout",
    )
    parser.add_argument(
        "-o", "--output",
        default="docs/ci-cd.md",
        help="Output markdown file path (default: docs/ci-cd.md)",
    )
    args = parser.parse_args()
    generate(args.ci_repo_path, args.output)


if __name__ == "__main__":
    main()
