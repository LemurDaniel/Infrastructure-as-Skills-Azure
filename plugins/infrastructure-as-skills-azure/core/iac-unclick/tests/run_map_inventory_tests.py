#!/usr/bin/env python3
"""Tests for scripts/map_inventory.py on a recorded inventory - no Azure, no login.

tests/fixtures/inventory-orders.json is a small portal-built group: a storage account with a
private endpoint, a lock, a diagnostic setting and a role assignment from the web app's
identity; a web app on its plan, integrated into a subnet of a network; a Databricks workspace,
a ReadOnly lock, a role assignment on the group, a Smart Detector rule and a Network Watcher.

The written spec must pass check_spec.py and be canonical, and:
  - the three resources are mapped, the plan and the private endpoint adopted as their parts,
    never as resources of their own;
  - live values are imported as they run (public access enabled, GRS), not the guardrail's;
  - the integration subnet is the network's part, the role assignment names both resources
    and keeps its id, the lock and the diagnostic setting are adopted;
  - what has no place is unmapped with its reason (Databricks, the ReadOnly lock, the group's
    role assignment), and the noise appears nowhere - nor does a tag Azure set itself.

Usage:
    python3 run_map_inventory_tests.py

Needs PyYAML. Exit 0 all pass, 1 a test failed, 2 could not run.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = os.path.join(HERE, '..', 'scripts', 'map_inventory.py')
FIXTURE = os.path.join(HERE, 'fixtures', 'inventory-orders.json')
CORE = os.path.join(HERE, '..', '..')
CHECK = os.path.join(CORE, 'iac-authoring', 'scripts', 'check_spec.py')
WRITE = os.path.join(CORE, 'iac-authoring', 'scripts', 'write_spec.py')


def main():
    try:
        import yaml
    except ImportError:
        print('[fail] no YAML parser available - pip install pyyaml')
        return 2
    failures = []

    def expect(cond, what):
        print(f"[{' ok ' if cond else 'fail'}] {what}")
        if not cond:
            failures.append(what)

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, 'infra-spec.yaml')
        r = subprocess.run([sys.executable, MAP, FIXTURE, '--stage', 'production', '--language', 'de', '--out', out],
                           capture_output=True, text=True)
        expect(r.returncode == 0, f"map_inventory.py writes the spec (exit {r.returncode}) {r.stdout[-300:]}{r.stderr[-300:]}")
        if r.returncode != 0:
            return 1
        c = subprocess.run([sys.executable, CHECK, out], capture_output=True, text=True)
        expect(c.returncode == 0, f"check_spec.py passes {c.stdout[-500:] if c.returncode else ''}")
        w = subprocess.run([sys.executable, WRITE, out, '--check', '--no-stamp'], capture_output=True, text=True)
        expect(w.returncode == 0, 'the spec is canonical')
        with open(out, encoding='utf-8') as f:
            text = f.read()
        spec = yaml.safe_load(text)

    res = spec.get('resources') or {}
    expect(set(res) == {'virtual-network', 'storage-account', 'app-service'},
           f"three resources mapped, no part as its own resource: {sorted(res)}")
    st, app = res.get('storage-account', {}), res.get('app-service', {})
    parts = lambda r: (r.get('adopt', {}).get('parts', {}).get('value', {}) or {}).get('production', [])
    expect(any('privateEndpoints/pe-st-blob' in p for p in parts(st)), 'the private endpoint is a part of the storage account')
    expect(any('serverFarms/asp-orders-prod' in p for p in parts(app)), 'the plan is a part of the web app')
    expect(st.get('networking', {}).get('public_network_access') == {'value': 'enabled', 'source': 'imported'},
           'public access imported as it runs, not the guardrail')
    expect(st.get('data_protection', {}).get('replication', {}).get('value') == 'GRS', 'replication read through its format')
    expect('lock_id' in st.get('adopt', {}) and 'diagnostic_setting_id' in st.get('adopt', {}),
           'the lock and the diagnostic setting adopted')
    expect(app.get('networking', {}).get('integration_subnet', {}).get('value') == {'resource': 'virtual-network', 'part': 'snet-app'},
           'the integration subnet is the network part')
    ra = (spec.get('wiring', {}).get('role_assignments', {}).get('value') or [{}])[0]
    expect(ra.get('from') == 'app-service' and ra.get('to') == 'storage-account' and ra.get('adopt_id'),
           'the role assignment names both resources and keeps its id')
    reasons = {(u['type'].lower(), u['reason']) for u in spec.get('unmapped') or []}
    for t, why in [('microsoft.databricks/workspaces', 'no_question_set'),
                   ('microsoft.authorization/locks', 'outside_lock_policy'),
                   ('microsoft.authorization/roleassignments', 'scope_not_adopted')]:
        expect((t, why) in reasons, f"unmapped: {t} ({why})")
    expect('NetworkWatcher' not in text and 'Failure Anomalies' not in text, 'the noise is left out')
    expect('hidden-link' not in text and spec['context'].get('tags') == {'owner_team': 'orders'},
           'tags Azure sets itself are left out, the shared one kept')

    print('-' * 70)
    print('all passed' if not failures else f"{len(failures)} failed")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
