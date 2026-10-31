#!/usr/bin/env python3
"""Runs the repository checks a pull request and a release both run.

Called by check.pull-request.yaml and release.plugin.yaml; runs locally the same way. The
checks run with the interpreter this script runs with, cheapest first, and the first that
fails stops the run with its exit code.

Usage:
    python3 .github/scripts/run_repository_checks.py     # Linux, macOS, CI
    python .github/scripts/run_repository_checks.py      # Windows

Needs PyYAML (pip install pyyaml). Exit 0 all passed, else the failing check's code.
"""

#
#   Chapters:
#     RUN THE CHECKS   One check after the other, stopping at the first failure.
#

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = 'plugins/infrastructure-as-skills-azure'
CHECKS = [
    '.claude/skills/git-commit-conventions/scripts/check_repo_consistency.py',
    f'{PLUGIN_DIR}/core/iac-authoring/scripts/check_question_set.py',
    f'{PLUGIN_DIR}/core/iac-authoring/tests/run_interview_digest_tests.py',
    f'{PLUGIN_DIR}/core/iac-diagram/tests/run_diagram_tests.py',
]


# ===========================================================================
# ===========================   RUN THE CHECKS   ============================
# ===========================================================================
#
#   main   Runs every check from the repository root, stops at the first failure.
#

def main():
    """Runs the checks in order. Returns 0, or the exit code of the first that failed."""
    for check in CHECKS:
        print(f"::group::{check}", flush=True)
        result = subprocess.run([sys.executable, check], cwd=ROOT)
        print("::endgroup::", flush=True)
        if result.returncode != 0:
            print(f"::error::{check} failed (exit {result.returncode})")
            return result.returncode
    return 0


if __name__ == '__main__':
    sys.exit(main())
