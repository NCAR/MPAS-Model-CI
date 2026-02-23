#!/usr/bin/env python3
"""
Compare MPAS-A log files against a reference standard.

Parses global min/max values for u and w at each timestep and compares
them to a reference log file, reporting percent differences.
"""

import argparse
import re
import sys
from pathlib import Path


def parse_log_file(filepath):
    """
    Parse an MPAS log file and extract global min/max values for u and w.
    
    Returns a list of dicts with keys: w_min, w_max, u_min, u_max
    """
    pattern_w = re.compile(r'global min, max w\s+([-\d.E+]+)\s+([-\d.E+]+)')
    pattern_u = re.compile(r'global min, max u\s+([-\d.E+]+)\s+([-\d.E+]+)')
    
    timesteps = []
    current_step = {}
    
    with open(filepath, 'r') as f:
        for line in f:
            match_w = pattern_w.search(line)
            match_u = pattern_u.search(line)
            
            if match_w:
                current_step['w_min'] = float(match_w.group(1))
                current_step['w_max'] = float(match_w.group(2))
            
            if match_u:
                current_step['u_min'] = float(match_u.group(1))
                current_step['u_max'] = float(match_u.group(2))
                # u comes after w, so this completes a timestep
                if 'w_min' in current_step:
                    timesteps.append(current_step)
                    current_step = {}
    
    return timesteps


def calc_percent_error(test_val, ref_val):
    """Calculate percent error, handling zero reference values."""
    if ref_val == 0:
        if test_val == 0:
            return 0.0
        else:
            return float('inf')
    return abs((test_val - ref_val) / ref_val) * 100


def compare_logs(test_file, ref_file):
    """
    Compare test log against reference log.
    
    Returns dict with comparison results.
    """
    test_data = parse_log_file(test_file)
    ref_data = parse_log_file(ref_file)
    
    if not test_data:
        return {
            'status': 'FAILED',
            'reason': 'No timesteps found in test file',
            'timesteps_test': 0,
            'timesteps_ref': len(ref_data)
        }
    
    if not ref_data:
        return {
            'status': 'ERROR',
            'reason': 'No timesteps found in reference file',
            'timesteps_test': len(test_data),
            'timesteps_ref': 0
        }
    
    # Compare timestep by timestep
    n_compare = min(len(test_data), len(ref_data))
    
    max_errors = {'w_min': 0, 'w_max': 0, 'u_min': 0, 'u_max': 0}
    sum_errors = {'w_min': 0, 'w_max': 0, 'u_min': 0, 'u_max': 0}
    
    for i in range(n_compare):
        for key in ['w_min', 'w_max', 'u_min', 'u_max']:
            err = calc_percent_error(test_data[i][key], ref_data[i][key])
            max_errors[key] = max(max_errors[key], err)
            sum_errors[key] = sum_errors[key] + err
    
    avg_errors = {k: v / n_compare for k, v in sum_errors.items()}
    
    # Determine overall status
    # Consider it a match if max error is < 1% for all fields
    threshold = 1.0
    if all(v < threshold for v in max_errors.values()):
        status = 'MATCH'
    elif all(v < 5.0 for v in max_errors.values()):
        status = 'CLOSE'
    else:
        status = 'DIFFER'
    
    return {
        'status': status,
        'timesteps_test': len(test_data),
        'timesteps_ref': len(ref_data),
        'timesteps_compared': n_compare,
        'max_errors': max_errors,
        'avg_errors': avg_errors
    }


def find_log_files(directory):
    """Find all MPAS log files in a directory tree."""
    log_files = []
    for path in Path(directory).rglob('log.atmosphere.*.out'):
        log_files.append(path)
    return log_files


def main():
    parser = argparse.ArgumentParser(
        description='Compare MPAS log files against a reference standard'
    )
    parser.add_argument(
        'logs_dir',
        help='Directory containing log file artifacts (each in subdirectory)'
    )
    parser.add_argument(
        'reference',
        help='Reference log file to compare against'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=1.0,
        help='Percent error threshold for MATCH status (default: 1.0)'
    )
    parser.add_argument(
        '--allow-missing',
        action='store_true',
        default=False,
        help='Do not fail if some configurations have no log files (e.g. due to infrastructure issues)'
    )
    
    args = parser.parse_args()
    
    if not Path(args.reference).exists():
        print(f"ERROR: Reference file not found: {args.reference}")
        sys.exit(1)
    
    if not Path(args.logs_dir).exists():
        print(f"ERROR: Logs directory not found: {args.logs_dir}")
        sys.exit(1)
    
    # Parse reference file
    ref_data = parse_log_file(args.reference)
    print(f"Reference: {args.reference}")
    print(f"  Timesteps: {len(ref_data)}")
    print()
    
    # Find and compare all log files
    results = []
    
    for log_dir in sorted(Path(args.logs_dir).iterdir()):
        if not log_dir.is_dir():
            continue
        
        # Extract config from directory name
        # Format: mpas_240km_1rank_logs_<compiler>_<mpi>_<gpu>_<io>
        name = log_dir.name
        
        log_files = list(log_dir.glob('log.atmosphere.*.out'))
        if not log_files:
            results.append({
                'name': name,
                'status': 'NO_LOG',
                'reason': 'No log file found'
            })
            continue
        
        log_file = log_files[0]
        result = compare_logs(log_file, args.reference)
        result['name'] = name
        results.append(result)
    
    # Print summary table
    print("=" * 90)
    print(f"{'Configuration':<55} {'Status':<8} {'Timesteps':<10} {'Max Err %':<12}")
    print("=" * 90)
    
    for r in results:
        name = r['name'].replace('mpas_240km_1rank_logs_', '')
        status = r['status']
        
        if status in ['MATCH', 'CLOSE', 'DIFFER']:
            timesteps = f"{r['timesteps_test']}/{r['timesteps_ref']}"
            max_err = max(r['max_errors'].values())
            max_err_str = f"{max_err:.4f}"
        elif status == 'NO_LOG':
            timesteps = '-'
            max_err_str = '-'
        else:
            timesteps = f"{r.get('timesteps_test', 0)}/{r.get('timesteps_ref', 0)}"
            max_err_str = '-'
        
        # Color coding for terminal
        if status == 'MATCH':
            status_str = f"\033[92m{status}\033[0m"  # Green
        elif status == 'CLOSE':
            status_str = f"\033[93m{status}\033[0m"  # Yellow
        elif status == 'NO_LOG':
            status_str = f"\033[91m{status}\033[0m"  # Red
        elif status == 'FAILED':
            status_str = f"\033[91m{status}\033[0m"  # Red
        else:
            status_str = f"\033[91m{status}\033[0m"  # Red
        
        print(f"{name:<55} {status_str:<17} {timesteps:<10} {max_err_str:<12}")
    
    print("=" * 90)
    
    # Print detailed errors for non-matching results
    print("\nDetailed comparison (max % error by field):")
    print("-" * 90)
    print(f"{'Configuration':<40} {'w_min':<12} {'w_max':<12} {'u_min':<12} {'u_max':<12}")
    print("-" * 90)
    
    for r in results:
        if r['status'] not in ['MATCH', 'CLOSE', 'DIFFER']:
            continue
        
        name = r['name'].replace('mpas_240km_1rank_logs_', '')
        if len(name) > 38:
            name = name[:38] + '..'
        
        errs = r['max_errors']
        print(f"{name:<40} {errs['w_min']:<12.6f} {errs['w_max']:<12.6f} "
              f"{errs['u_min']:<12.6f} {errs['u_max']:<12.6f}")
    
    print("-" * 90)
    
    # Summary counts
    n_match = sum(1 for r in results if r['status'] == 'MATCH')
    n_close = sum(1 for r in results if r['status'] == 'CLOSE')
    n_differ = sum(1 for r in results if r['status'] == 'DIFFER')
    n_no_log = sum(1 for r in results if r['status'] == 'NO_LOG')
    n_failed = sum(1 for r in results if r['status'] in ['FAILED', 'ERROR'])
    
    print(f"\nSummary: {n_match} MATCH, {n_close} CLOSE, {n_differ} DIFFER, "
          f"{n_failed} FAILED, {n_no_log} NO_LOG")
    
    # Exit with error if any actual failures or divergent results
    # --allow-missing tolerates NO_LOG (e.g. from infrastructure/pod failures)
    # but still fails on FAILED (log exists with 0 timesteps) and DIFFER
    if args.allow_missing:
        if n_failed > 0 or n_differ > 0:
            sys.exit(1)
        if n_no_log > 0:
            print(f"\nNote: {n_no_log} configuration(s) had no log files "
                  "(--allow-missing is set, not treated as failure)")
    else:
        if n_failed > 0 or n_differ > 0 or n_no_log > 0:
            sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
