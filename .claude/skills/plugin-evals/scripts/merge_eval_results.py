#!/usr/bin/env python3
"""Merges the aggregate-result.json of several `claude plugin eval` runs into one.

The CI workflow runs the suite one case at a time (`--case <name>`) so that it can say
which case it is on and how long the rest will take; the history and the summary still
want one run. The merged file has the shape of a single result: the cases of every input
in order, cost and duration summed, the earliest start, partial if any input was, and
the suite block of the first input without its case filter.

Usage:
    python3 merge_eval_results.py <result.json>... --out <merged.json> [--partial]

Exit 0 written, 2 no input could be read.
"""

import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('results', nargs='+', help='aggregate-result.json files, in case order')
    ap.add_argument('--out', required=True)
    ap.add_argument('--partial', action='store_true', help='cases were skipped (cost ceiling): mark the run partial')
    args = ap.parse_args()

    runs = []
    for path in args.results:
        try:
            with open(path, encoding='utf-8') as f:
                runs.append(json.load(f))
        except (OSError, ValueError) as e:
            print(f'skipped {path}: {e}', file=sys.stderr)
    if not runs:
        print('no result could be read', file=sys.stderr)
        return 2

    merged = dict(runs[0])
    merged['suite'] = {**(runs[0].get('suite') or {}), 'caseFilter': None}
    merged['startedAt'] = min(r.get('startedAt') or '' for r in runs) or runs[0].get('startedAt')
    merged['costUsd'] = sum(r.get('costUsd') or 0 for r in runs)
    merged['durationSeconds'] = sum(r.get('durationSeconds') or 0 for r in runs)
    merged['partial'] = args.partial or any(r.get('partial') for r in runs)
    merged['cases'] = [c for r in runs for c in r.get('cases', [])]
    # The suite totals are recomputed, never taken from the first input: weighted by the cases
    # each input carried, so a merged run reads like one run of all of them.
    aggs = [(r.get('aggregates') or {}) for r in runs]
    total = sum(a.get('casesTotal') or 0 for a in aggs)
    weighted = lambda key: (sum((a.get(key) or 0) * (a.get('casesTotal') or 0) for a in aggs) / total) if total else 0
    merged['aggregates'] = {
        'casesTotal': total,
        'casesPassed': sum(a.get('casesPassed') or 0 for a in aggs),
        'overallScore': weighted('overallScore'),
        'overallPassRate': weighted('overallPassRate'),
    }

    with open(args.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(merged, f, indent=1, ensure_ascii=False)
        f.write('\n')
    print(f"merged {len(runs)} result(s): {len(merged['cases'])} case(s), ${merged['costUsd']:.2f}, "
          f"{merged['durationSeconds']}s{' (partial)' if merged['partial'] else ''}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
