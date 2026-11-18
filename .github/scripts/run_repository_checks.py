#!/usr/bin/env python3
"""Runs the repository checks a pull request and a release both run.

Called by check.pull-request.yaml and release.plugin.yaml; runs locally the same way. Two
kinds of check, with the interpreter this script runs with:

  1. The checks over the whole repository, listed below: the consistency check, and the
     format checks of every question set, pattern and render map.
  2. Every test runner of the plugin - `core/*/tests/run_*_tests.py`, found, not listed. A
     runner that exists is a runner that runs: a hand-kept list left nine of them out, the
     pipeline, naming and version-gate tests among them.

All of them run even when one fails, so a pull request shows every failure at once.

Usage:
    python3 .github/scripts/run_repository_checks.py              # Linux, macOS, CI
    python .github/scripts/run_repository_checks.py               # Windows
    python3 .github/scripts/run_repository_checks.py -k pattern   # checks whose path contains "pattern"

Needs PyYAML (pip install pyyaml). The runners need nothing else: what wants draw.io,
terraform or bicep skips that case and says so. Exit 0 all passed, 1 at least one failed,
2 no check found.
"""

#
#   Chapters:
#     RUN THE CHECKS   Every check, the failures named at the end.
#

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = 'plugins/infrastructure-as-skills-azure'
REPOSITORY_CHECKS = [
    '.claude/skills/git-commit-conventions/scripts/check_repo_consistency.py',
    f'{PLUGIN_DIR}/core/iac-authoring/scripts/check_question_set.py',
    f'{PLUGIN_DIR}/core/iac-authoring/scripts/check_pattern.py',
    f'{PLUGIN_DIR}/core/iac-rendering/scripts/check_render_map.py',
]
TEST_RUNNERS = f'{PLUGIN_DIR}/core/*/tests/run_*_tests.py'


# ===========================================================================
# ===========================   RUN THE CHECKS   ============================
# ===========================================================================
#
#   checks   The repository checks, then every test runner the plugin holds.
#   main     Runs them all from the repository root and names the ones that failed.
#

def checks():
    """The repository checks in their order, then the test runners sorted by path."""
    runners = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob(TEST_RUNNERS))
    return REPOSITORY_CHECKS + runners


def main():
    """Runs every check. Returns 0, 1 when one failed, 2 when there is nothing to run."""
    ap = argparse.ArgumentParser(description='Run the repository checks.')
    ap.add_argument('-k', default='', help='only checks whose path contains this text')
    args = ap.parse_args()

    selected = [c for c in checks() if args.k in c]
    if not selected:
        print(f"::error::no check matches '{args.k}'")
        return 2

    failed = []
    for check in selected:
        print(f"::group::{check}", flush=True)
        started = time.monotonic()
        result = subprocess.run([sys.executable, check], cwd=ROOT)
        print("::endgroup::", flush=True)
        took = f"{time.monotonic() - started:.0f}s"
        if result.returncode != 0:
            print(f"::error::{check} failed (exit {result.returncode}, {took})", flush=True)
            failed.append(check)
        else:
            print(f"[ ok ] {check} ({took})", flush=True)

    print('-' * 70)
    if failed:
        print(f"{len(failed)} of {len(selected)} check(s) failed:")
        for check in failed:
            print(f"  {check}")
        return 1
    print(f"{len(selected)} check(s) passed.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
