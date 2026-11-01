#!/usr/bin/env python3
"""Tests for scripts/interview_digest.py: the digest drops nothing a run acts on.

For every question set in the plugin the digest of that set must carry each interview
question, each `forced_when` in full, each question with a derived `answer`,
`non_production_default` or `required`, and each boundary. A digest that loses one of
them is the ad-hoc extraction it replaces: a question asked that a rule settles. Then
`--why` must print the reasoning of the question named, `--language de` the German value
wording, and a set that does not exist must exit 2.

Usage:
    python3 run_interview_digest_tests.py

Needs PyYAML. Exit 0 all pass, 1 a test failed, 2 could not run.
"""

import io
import os
import subprocess
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'scripts', 'interview_digest.py')
sys.path.insert(0, os.path.join(HERE, '..', 'scripts'))


def main():
    try:
        import yaml
    except ImportError:
        print('[fail] no YAML parser available - pip install pyyaml')
        return 2
    import interview_digest as d

    sets = [d.DEPLOYMENT_SET]
    for root, _, files in os.walk(d.RESOURCES):
        if 'questions.yaml' in files:
            sets.append(os.path.join(root, 'questions.yaml'))

    failures, checked = [], 0
    for p in sorted(sets):
        with open(p, encoding='utf-8') as f:
            doc = yaml.safe_load(f)
        out = []
        d.digest(p, doc, 'en', set(), out)
        text = '\n'.join(out)
        rel = os.path.relpath(p, d.PLUGIN)
        for g, q in d.questions_of(doc):
            if q.get('resolved_by') == 'interview':
                checked += 1
                if f"] {q['id']}  " not in text:
                    failures.append(f"{rel}: interview question {q['id']} missing")
            elif d.acted_on(q):
                checked += 1
                if f"{g}.{q['id']}" not in text:
                    failures.append(f"{rel}: {g}.{q['id']} missing")
            ans = q.get('answer')
            if isinstance(ans, dict) and 'deployment' in ans and 'map' in ans:
                checked += 1
                if f"from deployment.{ans['deployment']} translated" not in text:
                    failures.append(f"{rel}: the deployment translation of {q['id']} missing")
            if q.get('forced_when') and d.flat(q['forced_when']) not in text:
                failures.append(f"{rel}: forced_when of {q['id']} missing")
            cat = q.get('accepts').get('catalogue') if isinstance(q.get('accepts'), dict) else None
            if cat:
                checked += 1
                if f"catalogue: {cat} (retrieved" not in text:
                    failures.append(f"{rel}: catalogue of {q['id']} missing or unread")
        for b in doc.get('boundaries') or []:
            checked += 1
            if d.flat(b) not in text:
                failures.append(f"{rel}: boundary missing: {b[:60]}")

    def run(*args):
        return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True,
                              text=True, encoding='utf-8')

    r = run('compute/app-service', '--why', 'deployment_slots')
    if 'why: Taken from the request' not in r.stdout:
        failures.append('--why deployment_slots did not print its why')
    if r.stdout.count('why: ') != 1:
        failures.append('--why printed more than the question named')
    r = run('compute/app-service', '--language', 'de')
    if 'genauso erreichbar wie die App' not in r.stdout:
        failures.append('--language de did not print the German value wording')
    if run('compute/no-such-set').returncode != 2:
        failures.append('a set that does not exist did not exit 2')

    for f in failures:
        print(f"[fail] {f}")
    print(f"{len(sets)} set(s), {checked} entries checked, {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
