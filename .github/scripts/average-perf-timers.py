#!/usr/bin/env python3
"""Average N parse-mpas-timers.py JSON outputs (repeated runs of the same
build) into a single timer JSON with the same schema, so downstream tooling
(summarize-perf.py) needs no changes.

Usage:
    average-perf-timers.py <in1.json> <in2.json> ... <inN.json> <out.json>
"""

import json
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "Usage: average-perf-timers.py <in1.json> [<in2.json> ...] <out.json>",
            file=sys.stderr,
        )
        return 2

    in_paths, out_path = sys.argv[1:-1], sys.argv[-1]
    runs = [json.load(open(p)) for p in in_paths]

    by_name = {}
    for run in runs:
        for row in run.get("timers", []):
            by_name.setdefault(row["name"], []).append(row)

    timers = []
    for name, rows in by_name.items():
        n = len(rows)
        timers.append(
            {
                "level": rows[0]["level"],
                "name": name,
                "total_s": sum(r["total_s"] for r in rows) / n,
                "calls": rows[0]["calls"],
                "min_s": min(r["min_s"] for r in rows),
                "max_s": max(r["max_s"] for r in rows),
                "avg_s": sum(r["avg_s"] for r in rows) / n,
                "pct_tot": sum(r["pct_tot"] for r in rows) / n,
                "pct_par": sum(r["pct_par"] for r in rows) / n,
                "par_eff": sum(r["par_eff"] for r in rows) / n,
                "n_runs_averaged": n,
            }
        )

    if any(len(rows) != len(in_paths) for rows in by_name.values()):
        print(
            "::warning::some timer names were not present in every run; "
            "averaged over whatever subset was available",
            file=sys.stderr,
        )

    with open(out_path, "w") as f:
        json.dump({"source_logs": in_paths, "timers": timers}, f, indent=2)

    print(f"Averaged {len(timers)} timer rows across {len(in_paths)} runs -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
