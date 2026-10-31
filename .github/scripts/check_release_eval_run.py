#!/usr/bin/env python3
"""Warns when a release has no Sonnet eval run, or the README badge names another version.

Called by release.plugin.yaml before a release is published. Warns, never fails on what it
finds: every release pull request records its Sonnet eval run on the eval-history branch
(git-commit-conventions, section 5), and the README badge shows the newest one with its
version and commit. A release without a run for its version is published anyway; the
warning says the badge still names an older version. A git error other than a missing
branch or pin fails the step.

Usage:
    python3 .github/scripts/check_release_eval_run.py <version>
    python3 .github/scripts/check_release_eval_run.py 0.7.0

Standard library only. Exit 0, 1 on an unexpected git error.
"""

#
#   Chapters:
#     HELPERS                            git and the workflow annotations.
#     CHECK THE EVAL RUN AND THE BADGE   The run of this version, then the pinned badge.
#

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL_MODEL = 'sonnet'
HISTORY_BRANCH = 'eval-history'
# README: .../Infrastructure-as-Skills-Azure/<40-hex eval-history commit>/badge-sonnet.json
BADGE_PIN_RE = re.compile(r'Infrastructure-as-Skills-Azure/([0-9a-f]{40})/badge-sonnet\.json')


# ===========================================================================
# ===============================   HELPERS   ===============================
# ===========================================================================
#
#   git       Runs git in the repository root, returns (exit code, stdout).
#   warning   Prints a workflow warning annotation.
#

def git(*args):
    """Runs git with the arguments given, never raising on its exit code.

    args  (Required) The git arguments, e.g. 'show', 'FETCH_HEAD:index.json'.

    Returns (exit code, stdout as text).
    """
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    return result.returncode, result.stdout


def warning(message):
    """Prints a warning annotation, shown on the run's summary."""
    print(f"::warning::{message}")


# ===========================================================================
# ====================   CHECK THE EVAL RUN AND THE BADGE   =================
# ===========================================================================
#
#   check_eval_run   Finds the Sonnet run recorded for this version.
#   check_badge      Checks that the README badge is pinned to a run of this version.
#   main             Both checks for the version given.
#

def check_eval_run(version):
    """Reports the Sonnet run of the version, or warns that there is none.

    version  (Required) The version about to be released, without the leading v.

    Returns False when eval-history does not exist (nothing was ever recorded), else True.
    """
    code, _ = git('fetch', '--quiet', 'origin', HISTORY_BRANCH)
    if code != 0:
        warning(f"no {HISTORY_BRANCH} branch: v{version} is released without a recorded eval run")
        return False
    code, index = git('show', 'FETCH_HEAD:index.json')
    if code != 0:
        raise RuntimeError(f"{HISTORY_BRANCH} has no index.json - the history branch is broken")

    runs = [r for r in json.loads(index).get('runs', []) if r.get('model') == EVAL_MODEL]
    own_runs = [r for r in runs if r.get('version') == version]
    if own_runs:
        run = own_runs[-1]
        full_count = sum(1 for c in run['cases'] if c.get('passRate') == 1)
        print(f"eval run for v{version}: {EVAL_MODEL} at {run.get('commit')}, "
              f"{full_count}/{len(run['cases'])} cases at 100%")
        return True

    last = runs[-1] if runs else None
    shown = f"v{last['version']} @ {(last.get('commit') or '')[:7]}" if last else 'nothing'
    warning(f"v{version} is released without a Sonnet eval run on {HISTORY_BRANCH}; "
            f"the README badge still shows {shown}. Run the suite (git-commit-conventions, section 5).")
    return True


def check_badge(version):
    """Warns unless the README badge is pinned to an eval-history commit of this version.

    version  (Required) The version about to be released, without the leading v.
    """
    pin = BADGE_PIN_RE.search((ROOT / 'README.md').read_text(encoding='utf-8'))
    if not pin:
        warning("the README badge is not pinned to an eval-history commit")
        return
    code, badge = git('show', f"{pin.group(1)}:badge-sonnet.json")
    if code != 0:
        warning(f"the README badge is pinned to {pin.group(1)}, which is not on {HISTORY_BRANCH}")
    elif f"v{version} " not in badge:
        other = re.search(r'v[0-9][^ ]*', badge)
        warning(f"the README badge is pinned to a run of another version ({other.group(0) if other else '?'}), not v{version}")
    else:
        print(f"README badge pinned to {pin.group(1)}: v{version}")


def main(argv):
    """Checks the eval run and the badge of the version in argv[0]. Returns the exit code."""
    if len(argv) != 1:
        print("usage: check_release_eval_run.py <version>")
        return 1
    version = argv[0].lstrip('v')
    if check_eval_run(version):
        check_badge(version)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
