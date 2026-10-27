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

--markdown writes the pull request comment for the run beside it: the pass rate per case,
a case that passed in some runs but not all marked unstable, and the change against the
newest run of an older plugin version on the same model - the comparison the dashboard
makes, with a link to the run there (--dashboard-url) and to the workflow run (--run-url).

Usage:
    python3 record_eval_history.py <aggregate-result.json> --history-dir <checkout> \
        --model haiku --trigger pr [--pr 57] [--commit <sha>] \
        [--markdown <comment.md> --dashboard-url <url> --run-url <url>]

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


def comment(entry, runs, dashboard_url, run_url):
    """The pull request comment: one table, the change against the previous version on the same model."""
    older = [r for r in runs if r.get('model') == entry['model']
             and version_key(r.get('version')) < version_key(entry['version'])]
    prev = older[-1] if older else None  # runs are oldest first
    prev_rates = {c['name']: c.get('passRate') for c in (prev or {}).get('cases', [])}

    rows, unstable, failed, regressed = [], 0, 0, 0
    for c in entry['cases']:
        rate = c.get('passRate')
        note = ''
        if rate is not None and 0 < rate < 1:
            unstable += 1
            note = 'unstable'
        elif rate == 0:
            failed += 1
            note = 'failed'
        before = prev_rates.get(c['name'])
        change = ''
        if prev and rate is not None and before is not None and abs(rate - before) > 0.1:
            change = f'{pct(before)} → {pct(rate)}'
            if rate < before:
                regressed += 1
                note = (note + ', ' if note else '') + 'regression'
        rows.append(f"| {c['name']} | {pct(rate)} | {change} | {note} |")

    full = sum(1 for c in entry['cases'] if c.get('passRate') == 1)
    head = [
        '<!-- plugin-evals -->',
        f"### Plugin evals · v{entry['version']} · {entry['model']} · {entry.get('runsPerCase') or '?'} run(s) per case",
        f"**{full}/{len(entry['cases'])} cases at 100%** · {unstable} unstable · {failed} failed · "
        f"{regressed} regression(s) · ${entry['costUsd']:.2f}" + (' · ⚠️ partial (cost ceiling)' if entry['partial'] else ''),
        '',
        f"Compared with v{prev['version']} on {entry['model']}." if prev
        else f"No older version on {entry['model']} to compare with yet.",
        '',
        f"| Case | Pass rate | vs v{prev['version']} | |" if prev else '| Case | Pass rate | | |',
        '|---|---|---|---|',
    ]
    links = []
    if dashboard_url:
        links.append(f"[Dashboard]({dashboard_url.rstrip('/')}/#run-{entry['id']})")
    if run_url:
        links.append(f'[Workflow run]({run_url})')
    return '\n'.join(head + rows + ([''] + [' · '.join(links)] if links else [])) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('result', help='aggregate-result.json of the run')
    ap.add_argument('--history-dir', required=True, help='checkout of the eval-history branch')
    ap.add_argument('--model', required=True, help='the model the agent ran on (haiku, sonnet, opus, ...)')
    ap.add_argument('--trigger', required=True, choices=['pr', 'release', 'manual'])
    ap.add_argument('--pr', type=int, default=None)
    ap.add_argument('--commit', default=None)
    ap.add_argument('--markdown', default=None, help='write the pull request comment to this file')
    ap.add_argument('--dashboard-url', default=None)
    ap.add_argument('--run-url', default=None)
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

    if args.markdown:
        with open(args.markdown, 'w', encoding='utf-8', newline='\n') as f:
            f.write(comment(entry, runs, args.dashboard_url, args.run_url))

    passed = sum(1 for c in entry['cases'] if c['passRate'] == 1)
    print(f"recorded v{version} on {args.model} ({args.trigger}): {passed}/{len(entry['cases'])} cases at 100%, "
          f"${entry['costUsd']:.2f}, {len(runs)} run(s) in the history")
    return 0


if __name__ == '__main__':
    sys.exit(main())
