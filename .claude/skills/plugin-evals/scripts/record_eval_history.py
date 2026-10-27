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
    python3 record_eval_history.py --history-dir <checkout> --overview-only

Every recording also rewrites the branch's README.md - per model a table of cases by plugin
version - and one badge-<model>.json per model in the shields.io endpoint format, which the
repository README shows.

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


def version_key(v):
    """x.y.z as numbers; a -suffix sorts before its release (0.6.0-rc1 < 0.6.0)."""
    core, _, pre = str(v or '0').partition('-')
    nums = [int(n) if n.isdigit() else 0 for n in core.split('.')]
    return nums + [0] * (3 - len(nums)), (pre == '', pre)


def pct(v):
    return '–' if v is None else f'{round(v * 100)}%'


def badge(run):
    """shields.io endpoint JSON for the newest run of a model: version, cases at 100%, the rest."""
    rates = [c.get('passRate') for c in run['cases']]
    full = sum(1 for r in rates if r == 1)
    failed = sum(1 for r in rates if r == 0)
    unstable = sum(1 for r in rates if r is not None and 0 < r < 1)
    parts = [f"v{run['version']}", f'{full}/{len(rates)}']
    if unstable:
        parts.append(f'{unstable} unstable')
    if failed:
        parts.append(f'{failed} failed')
    color = 'red' if failed else 'yellow' if unstable else 'brightgreen'
    return {'schemaVersion': 1, 'label': f"evals · {run['model']}", 'message': ' · '.join(parts), 'color': color}


def overview(runs):
    """README.md of the branch: per model one table, a row per case, a column per plugin version."""
    out = ['# eval-history', '',
           'Data branch, no code: one entry per eval run in `index.json`, the full result under',
           '`runs/<version>/<id>-<model>/`. Written by `record_eval_history.py` (repo skill `plugin-evals`),',
           'read by the eval dashboard. Pass rate = the share of runs in which every grader of the case passed;',
           'per plugin version its newest run on that model. ⬇/⬆ a change of more than 10 points against the',
           'previous version on the same model; a rate is never compared across models.', '']
    for model in sorted({r['model'] for r in runs}):
        mine = [r for r in runs if r['model'] == model]
        newest = {}
        for r in mine:  # oldest first, so the last one per version wins
            newest[r['version']] = r
        cols = sorted(newest.values(), key=lambda r: version_key(r['version']))
        cases = sorted({c['name'] for r in cols for c in r['cases']})
        last = cols[-1]
        out += [f"## {model}", '',
                f"![badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/"
                f"LemurDaniel/Infrastructure-as-Skills-Azure/eval-history/badge-{model}.json) "
                f"· newest: {last['trigger']}, {last.get('runsPerCase') or '?'} run(s) per case, "
                f"{last['startedAt'][:10]}", '',
                '| Case | ' + ' | '.join(f"v{r['version']}" for r in cols) + ' |',
                '|---|' + '---|' * len(cols)]
        for name in cases:
            cells, prev = [], None
            for r in cols:
                rate = next((c.get('passRate') for c in r['cases'] if c['name'] == name), None)
                mark = '🔴 ' if rate == 0 else '🟡 ' if rate is not None and rate < 1 else ''
                arrow = ''
                if prev is not None and rate is not None and abs(rate - prev) > 0.1:
                    arrow = ' ⬆' if rate > prev else ' ⬇'
                cells.append('' if rate is None else f'{mark}{pct(rate)}{arrow}')
                prev = rate if rate is not None else prev
            out.append(f'| {name} | ' + ' | '.join(cells) + ' |')
        out += ['| **cost** | ' + ' | '.join(f"${r.get('costUsd') or 0:.2f}" for r in cols) + ' |', '']
    return '\n'.join(out)


def write_overview(history_dir, runs):
    """Rewrites README.md and one badge-<model>.json per model from the whole index."""
    with open(os.path.join(history_dir, 'README.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(overview(runs))
    for model in {r['model'] for r in runs}:
        newest = [r for r in runs if r['model'] == model][-1]
        with open(os.path.join(history_dir, f'badge-{model}.json'), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(badge(newest), f)
            f.write('\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('result', nargs='?', help='aggregate-result.json of the run')
    ap.add_argument('--history-dir', required=True, help='checkout of the eval-history branch')
    ap.add_argument('--model', help='the model the agent ran on (haiku, sonnet, opus, ...)')
    ap.add_argument('--trigger', choices=['pr', 'release', 'manual'])
    ap.add_argument('--overview-only', action='store_true',
                    help='record nothing; rewrite README.md and the badges from index.json')
    ap.add_argument('--pr', type=int, default=None)
    ap.add_argument('--commit', default=None)
    args = ap.parse_args()

    if args.overview_only:
        with open(os.path.join(args.history_dir, 'index.json'), encoding='utf-8') as f:
            runs = json.load(f).get('runs', [])
        write_overview(args.history_dir, runs)
        print(f"overview written: {len(runs)} run(s), models {sorted({r['model'] for r in runs})}")
        return 0
    if not (args.result and args.model and args.trigger):
        ap.error('a result, --model and --trigger are required unless --overview-only')

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
    write_overview(args.history_dir, runs)

    passed = sum(1 for c in entry['cases'] if c['passRate'] == 1)
    print(f"recorded v{version} on {args.model} ({args.trigger}): {passed}/{len(entry['cases'])} cases at 100%, "
          f"${entry['costUsd']:.2f}, {len(runs)} run(s) in the history")
    return 0


if __name__ == '__main__':
    sys.exit(main())
