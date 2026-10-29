#!/usr/bin/env python3
"""Checks that every decision in an infra-spec.yaml is asserted by the
rendered Terraform tests.

Read-only. The rendering contract (core/iac-rendering/SKILL.md) says a render
is not finished until every decision under `resources:` is asserted by exactly
one test, or named as not observable in a plan with its reason. This script
makes that a check instead of a claim.

It reads the spec's `resources:` block - every key path
`<resource>.<group>.<question>` that carries a `value` is a decision - and
scans the test files beside the spec for the markers each target's idiom
prescribes. Terraform, in `.tftest.hcl`:

    # decision: storage-account.security.min_tls_version
    # not-testable: storage-account.networking.allow_azure_services_bypass - <why>

Bicep, as entries of a `.armtest.yaml` list (run by run_arm_tests.py):

    - decision: storage-account.security.min_tls_version
      path: ...
      equals: TLS1_2
    - not_testable: storage-account.networking.allow_azure_services_bypass
      reason: <why>

Each kind of test file present is checked on its own: a directory holding
both must cover every decision in both.

Then:
  1. A decision with neither marker is unasserted. Error.
  2. A decision with both, or marked twice, is ambiguous. Error.
  3. A not-testable marker without a reason after the dash is a silence
     dressed up as a sentence. Error.
  4. A marker naming a decision the spec does not have is stale - the spec
     moved and the test did not. Error.
  5. A `# decision:` marker not followed by an `assert` block is a label on
     nothing. Error.

Needs PyYAML (pip install pyyaml). Without it the script says so and exits 2.

Usage:
    python3 check_render_coverage.py ./infra/infra-spec.yaml [--tests <dir>]

Exit 0 every decision covered, 1 gaps or stale markers, 2 could not check.
"""

import argparse
import glob
import os
import re
import sys

COLORS = {'cyan': '36', 'green': '32', 'red': '31', 'gray': '90'}
USE_COLOR = sys.stdout.isatty() and not os.environ.get('NO_COLOR')


def say(text, color=None):
    if color and USE_COLOR:
        print(f"\033[{COLORS[color]}m{text}\033[0m")
    else:
        print(text)


def ok(text): say(f"[ ok ] {text}", 'green')
def bad(text): say(f"[fail] {text}", 'red')


DECISION_RE = re.compile(r'^\s*#\s*decision:\s*([A-Za-z0-9_.\-]+)\s*$')
NOT_TESTABLE_RE = re.compile(r'^\s*#\s*not-testable:\s*([A-Za-z0-9_.\-]+)\s*(-\s*(.*))?$')
COMMENT_OR_BLANK_RE = re.compile(r'^\s*(#.*)?$')
ASSERT_RE = re.compile(r'^\s*assert\s*\{')
COMMENT_TEXT_RE = re.compile(r'^\s*#\s*(\S.*)$')
MARKER_RE = re.compile(r'^\s*#\s*(decision|not-testable):')


def main():
    ap = argparse.ArgumentParser(description='Check that every spec decision is asserted by the rendered Terraform tests.')
    ap.add_argument('spec', help='the infra-spec.yaml; tests are looked up in tests/ beside it unless --tests says otherwise')
    ap.add_argument('--tests', help='directory holding the .tftest.hcl files (default: <spec dir>/tests)')
    args = ap.parse_args()

    if not os.path.isfile(args.spec):
        bad(f"no such file: {args.spec}")
        return 2
    spec_path = os.path.abspath(args.spec)
    base = os.path.dirname(spec_path)
    # Tests sit in tests/ beside the spec and, for a render grouped into family modules, in
    # modules/<family>/tests/ - one unit per family. --tests names one directory instead.
    if args.tests:
        tests_dirs = [os.path.abspath(args.tests)]
    else:
        tests_dirs = [os.path.join(base, 'tests')]
        tests_dirs += sorted(glob.glob(os.path.join(base, 'modules', '*', 'tests')))
    tests_dirs = [d for d in tests_dirs if os.path.isdir(d)]
    if not tests_dirs:
        bad(f"no tests directory at {os.path.join(base, 'tests')} - a render without tests is not finished")
        return 1

    def listing(suffix):
        found = []
        for d in tests_dirs:
            for f in sorted(os.listdir(d)):
                if f.endswith(suffix) and os.path.isfile(os.path.join(d, f)):
                    found.append(os.path.relpath(os.path.join(d, f), base).replace(os.sep, '/'))
        return found

    tf_files = listing('.tftest.hcl')
    arm_files = listing('.armtest.yaml')
    if not tf_files and not arm_files:
        bad(f"no .tftest.hcl or .armtest.yaml in {', '.join(tests_dirs)} - a render without tests is not finished")
        return 1

    # --- read the spec -----------------------------------------------------
    try:
        import yaml
    except ImportError:
        bad('no YAML parser available (pip install pyyaml)')
        return 2
    try:
        with open(spec_path, encoding='utf-8') as f:
            doc = yaml.safe_load(f)
    except yaml.YAMLError as e:
        bad(f"YAML does not parse: {e}")
        return 1

    # Every map carrying a `value` under resources: is a decision; its key path is its id.
    # A resource's `meta` describes it and renders nothing, so no test covers it.
    decisions = []

    def find(node, path):
        if not isinstance(node, dict):
            return
        if 'value' in node:
            decisions.append(path)
            return
        for k in node:
            if str(k).startswith('_') or (k == 'meta' and path.count('.') == 0 and path):
                continue
            find(node[k], f"{path}.{k}" if path else str(k))

    if isinstance(doc, dict) and 'resources' in doc:
        find(doc['resources'], '')

    say(f"Render coverage - {spec_path}", 'cyan')
    print('-' * 70)

    if not decisions:
        bad('the spec has no decisions under resources: - nothing to cover')
        return 1

    # --- read the markers --------------------------------------------------
    def read_tf(files):
        errors, asserted, marked = [], {}, {}
        for name in files:
            with open(os.path.join(base, name), encoding='utf-8') as f:
                lines = f.read().splitlines()
            for i, line in enumerate(lines):
                where = f"{name}:{i + 1}"

                m = DECISION_RE.match(line)
                if m:
                    did = m.group(1)
                    if did in asserted:
                        errors.append(f"{did} is asserted twice ({asserted[did]} and {where}); one assert per decision")
                    asserted[did] = where
                    # The next non-blank, non-comment line has to open an assert block.
                    j = i + 1
                    while j < len(lines) and COMMENT_OR_BLANK_RE.match(lines[j]):
                        j += 1
                    if j >= len(lines) or not ASSERT_RE.match(lines[j]):
                        errors.append(f"{did} at {where} is not followed by an assert block")
                    continue

                m = NOT_TESTABLE_RE.match(line)
                if m:
                    did = m.group(1)
                    reason = (m.group(3) or '').strip()
                    # The reason may continue on the next comment lines.
                    j = i + 1
                    while j < len(lines):
                        t = COMMENT_TEXT_RE.match(lines[j])
                        if not t or MARKER_RE.match(lines[j]):
                            break
                        reason += ' ' + t.group(1).strip()
                        j += 1
                    if not reason:
                        errors.append(f"{did} at {where} is marked not-testable without a reason after the dash")
                    if did in marked:
                        errors.append(f"{did} is marked not-testable twice ({marked[did]} and {where})")
                    marked[did] = where
        return errors, asserted, marked

    def read_arm(files):
        errors, asserted, marked = [], {}, {}
        for name in files:
            with open(os.path.join(base, name), encoding='utf-8') as f:
                try:
                    entries = yaml.safe_load(f) or []
                except yaml.YAMLError as e:
                    errors.append(f"{name}: YAML does not parse: {e}")
                    continue
            if not isinstance(entries, list):
                errors.append(f"{name}: the test file is a list of entries")
                continue
            for i, entry in enumerate(entries, 1):
                where = f"{name}#{i}"
                if not isinstance(entry, dict):
                    errors.append(f"{where} is not a mapping")
                    continue
                if 'decision' in entry:
                    did = str(entry['decision'])
                    if did in asserted:
                        errors.append(f"{did} is asserted twice ({asserted[did]} and {where}); one assert per decision")
                    asserted[did] = where
                    if not entry.get('path') or not any(k in entry for k in ('equals', 'contains', 'matches', 'absent')):
                        errors.append(f"{did} at {where} has no path or no operator - a label on nothing")
                elif 'not_testable' in entry:
                    did = str(entry['not_testable'])
                    if not str(entry.get('reason', '')).strip():
                        errors.append(f"{did} at {where} is marked not_testable without a reason")
                    if did in marked:
                        errors.append(f"{did} is marked not_testable twice ({marked[did]} and {where})")
                    marked[did] = where
        return errors, asserted, marked

    # --- compare, per kind of test file ------------------------------------
    errors = []
    kinds = []
    if tf_files:
        kinds.append(('terraform', tf_files, read_tf(tf_files)))
    if arm_files:
        kinds.append(('bicep', arm_files, read_arm(arm_files)))

    for kind, files, (kind_errors, asserted, marked) in kinds:
        errors.extend(f"{kind}: {e}" for e in kind_errors)
        covered = 0
        for d in decisions:
            a, n = d in asserted, d in marked
            if a and n:
                errors.append(f"{kind}: {d} is both asserted ({asserted[d]}) and marked not-testable ({marked[d]}) - pick one")
            elif not a and not n:
                errors.append(f"{kind}: {d} is neither asserted nor marked not-testable")
            else:
                covered += 1
        for did in list(asserted) + list(marked):
            if did not in decisions:
                where = asserted.get(did, marked.get(did))
                errors.append(f"{kind}: {did} (marker at {where}) is not a decision in the spec - stale marker")

        ok(f"{kind} - {len(decisions)} decision(s) in resources:, {len(asserted)} asserted, {len(marked)} marked not-testable, {len(files)} test file(s)")
        for did in sorted(marked):
            say(f"  not-testable: {did} ({marked[did]})", 'gray')

    print('-' * 70)
    if errors:
        bad(f"{len(errors)} gap(s)")
        for e in errors:
            say(f"         {e}", 'gray')
        return 1
    say(f"Every decision covered ({len(decisions)}/{len(decisions)}) in {', '.join(k for k, _, _ in kinds)}.", 'green')
    return 0


if __name__ == '__main__':
    sys.exit(main())
