#!/usr/bin/env python3
"""Parse the MPAS-A native timer table out of a log.atmosphere.*.out file.

MPAS-A prints a hierarchical timer table by default (TIMER_LIB unset ->
MPAS_NATIVE_TIMERS, see src/framework/mpas_timer.F: mpas_timer_write). This
table is emitted on every run, CPU or GPU, and includes per-routine wall-clock
timers (e.g. atm_advance_acoustic_step, atm_compute_dyn_tend) plus, on
OpenACC/GPU builds, additional "[ACC_data_xfer]" timers wrapping halo
exchanges. Parsing this table gives a routine-level CPU vs GPU comparison
with no source changes required.

Row format (mpas_timer.F, mpas_timer_write):
    write(msg,'(i2, 1x, a45, f15.5, i10, 3f15.5, 1x, f8.2, 3x, f8.2, 3x, f8.2)')
        levels, indentation // timer_name, total_time, calls, min_time, max_time,
        avg_time, pct_tot, pct_par, par_eff

Usage:
    parse-mpas-timers.py <log-file> <output-json>
"""

import json
import re
import sys

# Level (int) + indented name, then 8 trailing numeric fields:
#   total(f), calls(i), min(f), max(f), avg(f), pct_tot(f), pct_par(f), par_eff(f)
# Matched from the right via decimal points rather than fixed columns, since
# very long/deeply-nested names can overflow their fixed-width field in the
# Fortran output.
ROW_RE = re.compile(
    r"^\s*(?P<level>\d+)\s+(?P<name>.+?)\s+"
    r"(?P<total>\d+\.\d+)\s+(?P<calls>\d+)\s+"
    r"(?P<min>\d+\.\d+)\s+(?P<max>\d+\.\d+)\s+(?P<avg>\d+\.\d+)\s+"
    r"(?P<pct_tot>-?\d+\.\d+)\s+(?P<pct_par>-?\d+\.\d+)\s+(?P<par_eff>-?\d+\.\d+)\s*$"
)

HEADER_MARKER = "timer_name"


def parse_timer_table(text: str) -> list[dict]:
    lines = text.splitlines()

    # Find the header row so we only parse the table, not incidental matches
    # elsewhere in the log (there can be per-rank output for multiple ranks;
    # we intentionally only read rank 0's log, so there is exactly one table).
    start = None
    for i, line in enumerate(lines):
        if HEADER_MARKER in line and "total" in line and "pct_tot" in line:
            start = i + 1
            break

    if start is None:
        return []

    rows = []
    for line in lines[start:]:
        if not line.strip():
            # Native timer table is contiguous; a blank line ends it.
            if rows:
                break
            continue
        m = ROW_RE.match(line)
        if not m:
            # Table ended (next log section began)
            if rows:
                break
            continue
        rows.append(
            {
                "level": int(m.group("level")),
                "name": m.group("name").strip(),
                "total_s": float(m.group("total")),
                "calls": int(m.group("calls")),
                "min_s": float(m.group("min")),
                "max_s": float(m.group("max")),
                "avg_s": float(m.group("avg")),
                "pct_tot": float(m.group("pct_tot")),
                "pct_par": float(m.group("pct_par")),
                "par_eff": float(m.group("par_eff")),
            }
        )
    return rows


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: parse-mpas-timers.py <log-file> <output-json>", file=sys.stderr)
        return 2

    log_file, output_json = sys.argv[1], sys.argv[2]

    try:
        with open(log_file, "r", errors="replace") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"::error::log file not found: {log_file}", file=sys.stderr)
        return 1

    timers = parse_timer_table(text)

    if not timers:
        print(f"::warning::no timer table found in {log_file}", file=sys.stderr)

    with open(output_json, "w") as f:
        json.dump({"source_log": log_file, "timers": timers}, f, indent=2)

    print(f"Parsed {len(timers)} timer rows from {log_file} -> {output_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
