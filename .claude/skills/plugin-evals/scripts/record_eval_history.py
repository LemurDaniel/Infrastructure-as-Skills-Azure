#!/usr/bin/env python3
"""Records one `claude plugin eval` run in a checkout of the eval-history branch.

The branch is the memory of the suite across plugin versions and models, and the
eval dashboard reads it. This script only writes files into the checkout; the
workflow commits and pushes them.

    index.json                                  every run, oldest first: the summary the dashboard shows
    runs/<version>/<id>-<model>/aggregate-result.json   the full result, as the run wrote it
    runs/<version>/<id>-<model>/meta.json               what the result does not carry: model, trigger, PR, commit

The plugin version comes from the result (suite.plugins[0].version), the model from
--model: the result does not record it, and a Haiku run is never comparable with an
Opus run. Recording the same run twice replaces its entry instead of adding one.

Usage:
    python3 record_eval_history.py <aggregate-result.json> --history-dir <checkout> \
        --model sonnet --trigger release [--pr 57] [--commit <sha>]

Exit 0 recorded, 2 the result is unreadable or carries no plugin version.
"""

import argparse
import json
import os
import shutil
import sys


def summarize(result, meta):
    """One index entry: the fields the dashboard reads, per case the aggregate pass rates."""
    started = result.get('startedAt') or ''
    run_id = started.replace(':', '-').replace('.', '-')
    return {
        'id': run_id,
        **meta,
        'startedAt': started,
        'costUsd': result.get('costUsd') or 0,
        'durationSeconds': result.get('durationSeconds') or 0,
        'partial': bool(result.get('partial')),
        'runsPerCase': next((c.get('runsPerCase') for c in result.get('cases', []) if c.get('runsPerCase')), None),
        'cases': [
            {
                'name': c.get('name'),
                'passRate': (c.get('aggregates') or {}).get('passRate'),
                'passRateWithout': (c.get('aggregates') or {}).get('passRateWithout'),
                'delta': (c.get('aggregates') or {}).get('delta'),
            }
            for c in result.get('cases', [])
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('result', help='aggregate-result.json of the run')
    ap.add_argument('--history-dir', required=True, help='checkout of the eval-history branch')
    ap.add_argument('--model', required=True, help='the model the agent ran on (haiku, sonnet, opus, ...)')
    ap.add_argument('--trigger', required=True, choices=['pr', 'release', 'manual'])
    ap.add_argument('--pr', type=int, default=None)
    ap.add_argument('--commit', default=None)
    args = ap.parse_args()

    try:
        with open(args.result, encoding='utf-8') as f:
            result = json.load(f)
    except (OSError, ValueError) as e:
        print(f'cannot read {args.result}: {e}', file=sys.stderr)
        return 2
    plugins = (result.get('suite') or {}).get('plugins') or []
    version = plugins[0].get('version') if plugins else None
    if not version or not result.get('startedAt'):
        print(f'{args.result}: no plugin version or start time - not a run that can be recorded', file=sys.stderr)
        return 2

    meta = {'version': version, 'model': args.model, 'trigger': args.trigger, 'pr': args.pr,
            'commit': (args.commit or '')[:12] or None}
    entry = summarize(result, meta)

    run_dir = os.path.join(args.history_dir, 'runs', version, f"{entry['id']}-{args.model}")
    os.makedirs(run_dir, exist_ok=True)
    shutil.copyfile(args.result, os.path.join(run_dir, 'aggregate-result.json'))
    with open(os.path.join(run_dir, 'meta.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({**meta, 'id': entry['id']}, f, indent=2)
        f.write('\n')

    index_path = os.path.join(args.history_dir, 'index.json')
    index = {'schemaVersion': 1, 'runs': []}
    if os.path.exists(index_path):
        with open(index_path, encoding='utf-8') as f:
            index = json.load(f)
    runs = [r for r in index.get('runs', []) if not (r.get('id') == entry['id'] and r.get('model') == args.model)]
    runs.append(entry)
    runs.sort(key=lambda r: r.get('startedAt') or '')
    index['runs'] = runs
    with open(index_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(index, f, indent=1, ensure_ascii=False)
        f.write('\n')

    passed = sum(1 for c in entry['cases'] if c['passRate'] == 1)
    print(f"recorded v{version} on {args.model} ({args.trigger}): {passed}/{len(entry['cases'])} cases at 100%, "
          f"${entry['costUsd']:.2f}, {len(runs)} run(s) in the history")
    return 0


if __name__ == '__main__':
    sys.exit(main())
