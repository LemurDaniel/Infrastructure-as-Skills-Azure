#!/usr/bin/env python3
"""Runs the plugin's eval cases one by one under a cost ceiling and merges their results.

Called by eval.plugin.yaml; runs locally the same way. One case per call, so the log says
which case runs, how far along the suite is and how long the rest will take (the average of
the cases so far); the CLI itself prints only the final table. Each call gets what is left
of the cost ceiling. Report only: a failing case does not fail the run, a case without a
result is an error, and a suite without any result fails.

Requires: the Claude Code CLI (claude) on PATH and ANTHROPIC_API_KEY set; run from anywhere.

Usage:
    python3 .github/scripts/run_eval_suite.py --output-dir <dir> --model sonnet --max-cost-usd 30
    python3 .github/scripts/run_eval_suite.py --output-dir ./eval --model haiku --max-cost-usd 5 \\
        --runs 2 --tag terraform

Standard library only. Exit 0 merged, 1 nothing to run or no result.
"""

#
#   Chapters:
#     HELPERS         Duration format, the cost of a result, the arguments.
#     SELECT CASES    The cases that match the name glob and the tag.
#     RUN THE SUITE   One eval call per case, then the merged result.
#

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = 'plugins/infrastructure-as-skills-azure'
MERGE_SCRIPT = ROOT / '.claude/skills/plugin-evals/scripts/merge_eval_results.py'
MAX_PARALLEL = 8


# ===========================================================================
# ===============================   HELPERS   ===============================
# ===========================================================================
#
#   format_duration   Seconds as 3m07s.
#   case_cost         The costUsd of a case result, 0 when it has none.
#   parse_args        The command line.
#

def format_duration(seconds):
    """Formats seconds as minutes and seconds.

    format_duration(187)  => '3m07s'
    """
    seconds = int(seconds)
    return f"{seconds // 60}m{seconds % 60:02d}s"


def case_cost(result_path):
    """Returns the costUsd of an aggregate-result.json, 0.0 when it records none."""
    with open(result_path, encoding='utf-8') as f:
        return float(json.load(f).get('costUsd') or 0)


def parse_args(argv):
    """Parses the command line; every option of eval.plugin.yaml's dispatch has one here."""
    parser = argparse.ArgumentParser(description='Runs the plugin eval suite case by case.')
    parser.add_argument('--output-dir', required=True,
                        help='(Required) Where the case results and the merged aggregate-result.json go.')
    parser.add_argument('--model', required=True, choices=['sonnet', 'haiku', 'opus'],
                        help='(Required) The model the agent runs on.')
    parser.add_argument('--max-cost-usd', required=True, type=float,
                        help='(Required) The hard cost ceiling of the whole suite in USD.')
    parser.add_argument('--runs', default='',
                        help="(Optional) Runs for every case, in parallel up to 8. Empty: each case's own runs.")
    parser.add_argument('--case', default='',
                        help="(Optional) Case name glob, e.g. 'spec-*'. Empty: all cases.")
    parser.add_argument('--tag', default='',
                        help='(Optional) Only cases whose prompt.md carries this tag. Empty: all cases.')
    return parser.parse_args(argv)


# ===========================================================================
# ============================   SELECT CASES   =============================
# ===========================================================================
#
#   select_cases   Every case directory that matches the name glob and the tag.
#

def select_cases(case_glob, tag):
    """Returns the names of the matching cases, sorted by their path.

    case_glob  (Required) A shell glob on the case name, '' for all.
    tag        (Required) A tag of the prompt.md frontmatter, '' for all.

    select_cases('', 'terraform')  => ['language-en-request', 'requirements-stated', ...]
    """
    # The tags are in the prompt.md frontmatter: tags: [pr, terraform, ...]
    tag_re = re.compile(r'^tags:.*[\[ ,]' + re.escape(tag) + r'[\],]', re.MULTILINE)
    case_dirs = sorted(
        p.parent for p in (ROOT / PLUGIN_DIR / 'evals').rglob('case.yaml')
        if 'results' not in p.relative_to(ROOT / PLUGIN_DIR / 'evals').parts
    )
    selected = []
    for case_dir in case_dirs:
        if case_glob and not fnmatch.fnmatchcase(case_dir.name, case_glob):
            continue
        if tag and not tag_re.search((case_dir / 'prompt.md').read_text(encoding='utf-8')):
            continue
        selected.append(case_dir.name)
    return selected


# ===========================================================================
# ============================   RUN THE SUITE   ============================
# ===========================================================================
#
#   run_case   One `claude plugin eval` call with what is left of the ceiling.
#   main       Validations, the cases in order, then the merge.
#

def run_case(name, case_dir, args, budget, runs_args, parallel):
    """Runs one case and returns the CLI's exit code; a failing case is a result, not an error.

    name       (Required) The case name.
    case_dir   (Required) Where its result and report go.
    args       (Required) The parsed command line.
    budget     (Required) What is left of the cost ceiling, in USD.
    runs_args  (Required) ['--runs', n] or [] for each case's own runs.
    parallel   (Required) How many runs go in parallel.
    """
    # --threshold 0: report only. Exit 2 is the cost ceiling - partial results, still recorded.
    # --scaffold: the sync cases stage a repository first, and this is our own suite.
    command = [
        shutil.which('claude') or 'claude', 'plugin', 'eval', PLUGIN_DIR, '--case', name,
        '--model', args.model, '--judge-model', 'sonnet', *runs_args,
        '-j', str(parallel), '--ablation', 'none', '--max-cost-usd', str(budget),
        '--allow-tools', 'Write', 'Edit', '--trust-plugin', '--scaffold', '--no-publish', '--threshold', '0',
        '--output-dir', str(case_dir), '--report', str(case_dir / 'report.html'),
    ]
    return subprocess.run(command, cwd=ROOT).returncode


def main(argv):
    """Runs the suite as eval.plugin.yaml asks. Returns the exit code."""
    args = parse_args(argv)

    # Validations
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("::error::the repository secret ANTHROPIC_API_KEY is not set")
        return 1
    cases = select_cases(args.case, args.tag)
    if not cases:
        print(f"::error::no case matches case '{args.case}' and tag '{args.tag}'")
        return 1

    # Without --runs each case runs its own `runs:` from prompt.md; --runs would override them all.
    runs_args = ['--runs', args.runs] if args.runs else []
    parallel = min(int(args.runs), MAX_PARALLEL) if args.runs else MAX_PARALLEL
    output_dir = Path(args.output_dir).resolve()
    (output_dir / 'cases').mkdir(parents=True, exist_ok=True)
    tag_label = f" tagged {args.tag}" if args.tag else ''
    runs_label = args.runs or "the case's own"
    print(f"{len(cases)} case(s){tag_label} on {args.model}, {runs_label} run(s) each, "
          f"ceiling ${args.max_cost_usd}: {' '.join(cases)}", flush=True)

    # Cases
    started_at = time.monotonic()
    spent = 0.0
    is_partial = False      # set when the ceiling stops the suite early
    for i, name in enumerate(cases):
        elapsed = time.monotonic() - started_at
        eta = 'first case' if i == 0 else f"about {format_duration(elapsed / i * (len(cases) - i))} left"
        budget = round(max(0.0, args.max_cost_usd - spent), 2)
        if budget <= 0:
            print(f"::warning::cost ceiling ${args.max_cost_usd} reached after {i} of {len(cases)} case(s); the rest is skipped")
            is_partial = True
            break

        print(f"::group::[{i + 1}/{len(cases)}] {name} - {format_duration(elapsed)} elapsed, {eta}, ${spent} spent", flush=True)
        case_started_at = time.monotonic()
        case_dir = output_dir / 'cases' / name
        exit_code = run_case(name, case_dir, args, budget, runs_args, parallel)
        print("::endgroup::", flush=True)

        result_path = case_dir / 'aggregate-result.json'
        if not result_path.exists():
            print(f"::error::[{i + 1}/{len(cases)}] {name} produced no result (exit {exit_code})")
            continue
        spent = round(spent + case_cost(result_path), 2)
        print(f"[{i + 1}/{len(cases)}] {name} done in {format_duration(time.monotonic() - case_started_at)}, "
              f"exit {exit_code}, ${spent} spent so far", flush=True)

    # Merge
    results = sorted(str(p) for p in (output_dir / 'cases').glob('*/aggregate-result.json'))
    if not results:
        print("::error::no case produced a result")
        return 1
    merge = [sys.executable, str(MERGE_SCRIPT), *results, '--out', str(output_dir / 'aggregate-result.json')]
    if is_partial:
        merge.append('--partial')
    subprocess.run(merge, cwd=ROOT, check=True)
    print(f"suite done in {format_duration(time.monotonic() - started_at)}, ${spent}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
