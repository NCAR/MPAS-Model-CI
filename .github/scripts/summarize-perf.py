#!/usr/bin/env python3
"""Combine CPU and GPU MPAS timer JSON (from parse-mpas-timers.py) into:
  1. A markdown comparison table (written to GITHUB_STEP_SUMMARY by the caller)
  2. A single structured perf-result.json meant to be the durable record of
     this run — this is the file a future history/graph step would append
     to a time series from.

All run metadata is read from environment variables so the workflow doesn't
need a fragile positional CLI.

Required env vars: CPU_JSON, GPU_JSON, OUT_JSON, OUT_MD
Optional metadata env vars (all default to "unknown" if unset):
  REF, SHA, RESOLUTION, RUN_DURATION, COMPILER, MPI,
  CPU_RANKS, GPU_RANKS, RUNNER_GROUP, RUN_ID, RUN_URL, TARGET_ROUTINE
"""

import json
import os


def load_timers(path: str) -> dict:
    with open(path) as f:
        data = json.load(f)
    # Keyed by timer name; if a name repeats (shouldn't, but be defensive)
    # keep the first occurrence.
    out = {}
    for row in data.get("timers", []):
        out.setdefault(row["name"], row)
    return out


def fmt(x, digits=3):
    return f"{x:.{digits}f}"


def main() -> int:
    cpu_path = os.environ["CPU_JSON"]
    gpu_path = os.environ["GPU_JSON"]
    out_json = os.environ["OUT_JSON"]
    out_md = os.environ["OUT_MD"]

    meta = {
        "ref": os.environ.get("REF", "unknown"),
        "sha": os.environ.get("SHA", "unknown"),
        "resolution": os.environ.get("RESOLUTION", "unknown"),
        "run_duration": os.environ.get("RUN_DURATION", "unknown"),
        "compiler": os.environ.get("COMPILER", "unknown"),
        "mpi": os.environ.get("MPI", "unknown"),
        "cpu_ranks": os.environ.get("CPU_RANKS", "unknown"),
        "gpu_ranks": os.environ.get("GPU_RANKS", "unknown"),
        "runner_group": os.environ.get("RUNNER_GROUP", "unknown"),
        "run_id": os.environ.get("RUN_ID", "unknown"),
        "run_url": os.environ.get("RUN_URL", ""),
        "target_routine": os.environ.get("TARGET_ROUTINE", ""),
    }

    cpu_timers = load_timers(cpu_path)
    gpu_timers = load_timers(gpu_path)

    all_names = set(cpu_timers) | set(gpu_timers)
    comparison = []
    for name in all_names:
        c = cpu_timers.get(name)
        g = gpu_timers.get(name)
        speedup = None
        if c and g and g["total_s"] > 0:
            speedup = c["total_s"] / g["total_s"]
        comparison.append(
            {
                "name": name,
                "cpu_total_s": c["total_s"] if c else None,
                "cpu_calls": c["calls"] if c else None,
                "gpu_total_s": g["total_s"] if g else None,
                "gpu_calls": g["calls"] if g else None,
                "speedup_cpu_over_gpu": speedup,
            }
        )

    # Sort by whichever side has the larger total time, descending, so the
    # most expensive routines surface first regardless of which side is slower.
    def sort_key(row):
        vals = [v for v in (row["cpu_total_s"], row["gpu_total_s"]) if v is not None]
        return max(vals) if vals else 0.0

    comparison.sort(key=sort_key, reverse=True)

    result = {
        "meta": meta,
        "comparison": comparison,
        "cpu_timers_full": list(cpu_timers.values()),
        "gpu_timers_full": list(gpu_timers.values()),
    }

    with open(out_json, "w") as f:
        json.dump(result, f, indent=2)

    # --- Markdown summary ---
    lines = []
    lines.append("## CPU vs GPU performance (native MPAS timers)")
    lines.append("")
    lines.append(
        f"- **Ref:** `{meta['ref']}` @ `{meta['sha'][:12]}`  "
        f"- **Resolution:** {meta['resolution']}  "
        f"- **Run duration:** {meta['run_duration']}"
    )
    lines.append(
        f"- **Compiler/MPI:** {meta['compiler']}/{meta['mpi']}  "
        f"- **Ranks:** CPU={meta['cpu_ranks']}, GPU={meta['gpu_ranks']}  "
        f"- **Runner group:** {meta['runner_group']} (same hardware, both legs)"
    )
    if meta["target_routine"]:
        lines.append(f"- **Branch target routine:** `{meta['target_routine']}`")
    lines.append("")
    lines.append(
        "Wall-clock time per named MPAS timer. GPU-only rows (e.g. "
        "`[ACC_data_xfer]`) have no CPU counterpart and no speedup figure. "
        "This is not GPU kernel-level granularity — see the routine's own "
        "notes for a future Nsight-based pass."
    )
    lines.append("")
    lines.append("| Timer | CPU total (s) | GPU total (s) | Speedup (CPU/GPU) |")
    lines.append("|---|---:|---:|---:|")

    MAX_ROWS = 30
    shown = comparison[:MAX_ROWS]
    for row in shown:
        marker = " **\u2190 target**" if row["name"] == meta["target_routine"] else ""
        cpu_s = fmt(row["cpu_total_s"]) if row["cpu_total_s"] is not None else "\u2014"
        gpu_s = fmt(row["gpu_total_s"]) if row["gpu_total_s"] is not None else "\u2014"
        speedup = f"{row['speedup_cpu_over_gpu']:.2f}\u00d7" if row["speedup_cpu_over_gpu"] else "\u2014"
        lines.append(f"| `{row['name']}`{marker} | {cpu_s} | {gpu_s} | {speedup} |")

    if len(comparison) > MAX_ROWS:
        lines.append("")
        lines.append(
            f"_{len(comparison) - MAX_ROWS} more timer(s) omitted from this table; "
            "full data is in the uploaded perf-result.json artifact._"
        )

    cpu_total = cpu_timers.get("total time", {}).get("total_s")
    gpu_total = gpu_timers.get("total time", {}).get("total_s")
    if cpu_total and gpu_total:
        lines.append("")
        lines.append(
            f"**Overall wall time:** CPU {fmt(cpu_total)}s vs GPU {fmt(gpu_total)}s "
            f"({cpu_total / gpu_total:.2f}\u00d7)"
        )

    with open(out_md, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Wrote {out_json} and {out_md} ({len(comparison)} timer rows compared)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
