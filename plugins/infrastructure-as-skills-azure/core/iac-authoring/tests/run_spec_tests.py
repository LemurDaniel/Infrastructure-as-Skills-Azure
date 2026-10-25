#!/usr/bin/env python3
"""Tests for the resource-group rules of scripts/check_spec.py.

tests/fixtures/resource-groups.yaml is a valid spec with a split. It must pass clean; so must
the same spec with the split taken out (one group stays valid). Then each mutation breaks one rule
in a copy - a role that does not exist, a mode missing, a placement into a group the deployment
does not have - and the check must fail with the message that names it. A mutation whose text is no
longer in the fixture fails the run: a test that cannot break anything proves nothing.

Usage:
    python3 run_spec_tests.py

Needs PyYAML. Exit 0 all pass, 1 a test failed, 2 could not run.
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, '..', 'scripts', 'check_spec.py')
FIXTURE = os.path.join(HERE, 'fixtures', 'resource-groups.yaml')

SPLIT = "  resource_group_split: { value: [network, data, observability], source: stated }\n"
MODE_DATA = "  resource_group_mode_data: { value: create, source: stated }\n"

# (name, find, replace, expected substring of the output; None = must pass)
MUTATIONS = [
    ('the split names main', SPLIT, "  resource_group_split: { value: [main, network, data, observability], source: stated }\n", "lists 'main'"),
    ('the split names a role that does not exist', SPLIT, "  resource_group_split: { value: [network, data, observability, frontend], source: stated }\n", "'frontend', which is not one of"),
    ('the split names a role twice', SPLIT, "  resource_group_split: { value: [network, data, data, observability], source: stated }\n", 'twice'),
    ('the split is not a list', SPLIT, "  resource_group_split: { value: network, source: stated }\n", 'not a list of roles'),
    ('a split role has no mode', MODE_DATA, '', 'resource_group_mode_data is missing'),
    ('the main group has no mode', "  resource_group_mode_main: { value: create, source: stated }\n", '', 'resource_group_mode_main is missing'),
    ('a mode that is neither existing nor create', MODE_DATA, "  resource_group_mode_data: { value: destroy, source: stated }\n", "is not existing or create"),
    ('a mode for a role that is not split off', MODE_DATA, MODE_DATA + "  resource_group_mode_security: { value: create, source: stated }\n", 'resource_group_mode_security is stale'),
    ('a name for a role that is not split off', "  resource_group_name_network:\n", "  resource_group_name_security:\n    production: rg-sec-prod-we\n  resource_group_name_network:\n", 'resource_group_name_security is stale'),
    ('a placement into a role that is not split off', 'resource_group: { value: data,', 'resource_group: { value: security,', 'names a group the deployment does not have'),
    ('a placement into a group that does not exist', 'resource_group: { value: data,', 'resource_group: { value: frontend,', 'names a group the deployment does not have'),
    ('a placement without its reason', ', reason: the vault is kept with the data it protects', '', 'overridden with no reason'),
    ('a lock value that does not exist', "  resource_group_lock: { value: production, source: default }\n", "  resource_group_lock: { value: forever, source: default }\n", "resource_group_lock 'forever'"),
    ('a resource lock value that does not exist', "  resource_group_lock: { value: production, source: default }\n", "  resource_group_lock: { value: production, source: default }\n  resource_lock: { value: forever, source: default }\n", "resource_lock 'forever'"),
]

# The same spec without a split: every resource group line and the placement taken out.
NO_SPLIT = [
    SPLIT, "  resource_group_mode_main: { value: create, source: stated }\n",
    "  resource_group_mode_network: { value: existing, source: stated }\n", MODE_DATA,
    "  resource_group_mode_observability: { value: create, source: asked }\n",
    "  resource_group_lock: { value: production, source: default }\n",
    "  resource_group_name_network:\n    production: rg-spoke-shop-prod-we\n",
    "    placement:\n      resource_group: { value: data, source: overridden, reason: the vault is kept with the data it protects }\n",
]


def run(text):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'infra-spec.yaml')
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
        proc = subprocess.run([sys.executable, '-I', CHECK, path], capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def main():
    try:
        import yaml  # noqa: F401
    except ImportError:
        print('[fail] no YAML parser available (pip install pyyaml)')
        return 2
    with open(FIXTURE, encoding='utf-8', newline='') as f:
        base = f.read().replace('\r\n', '\n')

    failed = 0

    def report(ok, name, detail=''):
        nonlocal failed
        print(f"[{' ok ' if ok else 'fail'}] {name}")
        if not ok:
            failed += 1
            print(f"         {detail}")

    rc, out = run(base)
    report(rc == 0 and 'resource groups - main and 3 split role(s), 1 placement(s)' in out, 'the fixture passes', out[-400:])

    text = base
    for cut in NO_SPLIT:
        if cut not in text:
            report(False, 'one group stays valid', f"the fixture no longer holds: {cut!r}")
            break
        text = text.replace(cut, '')
    else:
        rc, out = run(text)
        report(rc == 0 and 'resource groups' not in out.replace('Resource groups', ''), 'without a split, one group stays valid', out[-400:])

    for name, find, replace, expected in MUTATIONS:
        if base.count(find) != 1:
            report(False, name, f"the mutation text is in the fixture {base.count(find)} times: {find[:60]!r}")
            continue
        rc, out = run(base.replace(find, replace))
        report(rc == 1 and expected in out, f"breaks: {name}", f"expected exit 1 with {expected!r}; got exit {rc}:\n{out[-500:]}")

    print('-' * 70)
    total = 2 + len(MUTATIONS)
    print(f"{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
