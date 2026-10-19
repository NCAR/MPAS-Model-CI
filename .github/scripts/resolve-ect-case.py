#!/usr/bin/env python3
"""Resolve one ECT case from .github/ect-cases.yml: defaults merged with the case, printed as key=value lines.

usage: resolve-ect-case.py [--case NAME] [--table PATH]      (empty/omitted case = the table's `default`)
       resolve-ect-case.py --data KEY                         (release tag and asset of a test-data archive: tag=..., asset=...)
Output keys: case, resolution, summary-file, restart-file, spinup-duration, run-duration,
ensemble-size, perturb-variable, perturb-magnitude, excluded-vars.
"""
import argparse, sys
from pathlib import Path
try:
    import yaml
except ImportError:
    sys.exit("::error::PyYAML is required (pip install pyyaml)")
ap = argparse.ArgumentParser()
ap.add_argument('--case', default=''); ap.add_argument('--data', default='')
ap.add_argument('--table', default=str(Path(__file__).resolve().parent.parent / 'ect-cases.yml'))
a = ap.parse_args()
t = yaml.safe_load(open(a.table))
cases = t.get('cases') or {}
if a.data:
    d = (t.get('data') or {}).get(a.data)
    if not d or not d.get('tag'):
        sys.exit(f"::error::No test data '{a.data}' under `data` in {a.table}. Available: {', '.join(t.get('data') or {})}")
    print(f"tag={d['tag']}\nasset={d.get('asset', a.data + '.tar.gz')}"); sys.exit(0)
name = a.case.strip() or t['default']
if name not in cases:
    sys.exit(f"::error::Unknown ECT case '{name}' in {a.table}. Available: {', '.join(cases)}")
r = dict(t.get('defaults') or {}); r.update(cases[name] or {})
required = ['resolution', 'summary-file', 'restart-file', 'spinup-duration', 'run-duration', 'perturb-variable',
            'perturb-magnitude', 'excluded-vars']
missing = [k for k in required if r.get(k) in (None, '')]
if missing:
    sys.exit(f"::error::ECT case '{name}' is missing required field(s): {', '.join(missing)}")
for k in ['resolution', 'summary-file', 'restart-file', 'spinup-duration', 'run-duration', 'perturb-variable',
          'perturb-magnitude', 'excluded-vars']:
    if k in r and not isinstance(r[k], str):
        sys.exit(f"::error::ECT case '{name}': field {k} must be a quoted string in {a.table} (got {type(r[k]).__name__} {r[k]!r}; "
                 "YAML turns unquoted durations like 1_00:00:00 into numbers)")
out = {'case': name}
for k in ['resolution', 'summary-file', 'restart-file', 'spinup-duration', 'run-duration', 'ensemble-size', 'perturb-variable',
          'perturb-magnitude', 'excluded-vars']:
    out[k] = str(r.get(k, '')).strip()
for k, v in out.items():
    if '\n' in v:
        sys.exit(f"::error::ECT case field {k} must be a single line")
    print(f"{k}={v}")
