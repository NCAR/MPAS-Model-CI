#!/usr/bin/env python3
"""Resolve one ECT case from .github/ect-cases.yml (see .github/ECT_CASES.md), printed as key=value lines.

usage: resolve-ect-case.py [--case NAME] [--table PATH]      (empty/omitted case = the table's `default`)
       resolve-ect-case.py --data KEY                         (release tag and asset of a test-data archive: tag=..., asset=...)
Output keys: case, resolution (the case's first data entry), summary-file, restart-file, spinup-duration, run-duration,
ensemble-size, perturb-variable, perturb-magnitude, excluded-vars, boundary-mask (true/false).
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
data, cases = t.get('data') or {}, t.get('cases') or {}

if a.data:
    d = data.get(a.data)
    if not d or not d.get('tag'):
        sys.exit(f"::error::No test data '{a.data}' under `data` in {a.table}. Available: {', '.join(data)}")
    print(f"tag={d['tag']}\nasset={d.get('asset', a.data + '.tar.gz')}"); sys.exit(0)

name = a.case.strip() or t['default']
if name not in cases:
    sys.exit(f"::error::Unknown ECT case '{name}' in {a.table}. Available: {', '.join(cases)}")
c = cases[name] or {}
def fail(msg): sys.exit(f"::error::ECT case '{name}' in {a.table}: {msg} (see .github/ECT_CASES.md)")

unknown = set(c) - {'description', 'data', 'ensemble', 'assets'}
if unknown:
    fail(f"unknown or not yet supported field(s): {', '.join(sorted(unknown))}")
d = c.get('data') or []
if not d:
    fail("`data` must list at least one entry")
if len(d) > 1:
    fail("more than one `data` entry is not supported yet")
for k in d:
    if k not in data:
        fail(f"data '{k}' is not listed under the top-level `data`")
e, s = c.get('ensemble') or {}, c.get('assets') or {}
p = e.get('perturb') or {}
out = {'case': name, 'resolution': d[0],
       'summary-file': s.get('summary'), 'restart-file': s.get('restart'),
       'spinup-duration': e.get('spinup'), 'run-duration': e.get('run'), 'ensemble-size': e.get('size'),
       'perturb-variable': p.get('variable'), 'perturb-magnitude': p.get('magnitude'),
       'excluded-vars': e.get('excluded-vars')}
bm = e.get('boundary-mask', False)
if not isinstance(bm, bool):
    fail(f"ensemble.boundary-mask must be true or false (got {bm!r})")
missing = [k for k, v in out.items() if v in (None, '')]
if missing:
    fail(f"missing value(s) for: {', '.join(missing)}")
for k in ['spinup-duration', 'run-duration', 'perturb-magnitude']:
    if not isinstance(out[k], str):
        fail(f"{k} must be a quoted string (got {out[k]!r}; YAML turns unquoted durations like 1_00:00:00 into numbers)")
out['boundary-mask'] = 'true' if bm else 'false'
for k, v in out.items():
    v = str(v).strip()
    if '\n' in v:
        fail(f"{k} must be a single line")
    print(f"{k}={v}")
