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
    role assignment), and the noise appears nowhere - nor does a tag Azure set itself;
  - the exposure follows from what was read (a public storage account: public);
  - the decision document lists the departures from the rules (public access, shared keys)
    and what was found and not built;
  - the one workspace the storage account's setting writes to is the deployment's destination;
    the web app and the network, without one, take workspace `none` and no other diagnostic decision.

tests/fixtures/inventory-network.json is a real group, anonymised: a vault behind a private
endpoint (and its network interface), a network of six subnets and three NSGs with rules of
their own, Deny among them; no diagnostic setting anywhere, the settings read. Its spec must:
  - read every NSG rule as it runs, a Deny kept, prefixes merged from both fields;
  - read no deny-all at 4096 as azure_default, never assume the default;
  - name the subnets each NSG guards as the network's parts (the NSG row spells their ids in
    upper case), so check_spec.py reports no subnet without one;
  - count the private endpoint's network interface as noise, not as unmapped;
  - read the vault's endpoint subnet from the row of its adopted private endpoint;
  - write observability_ownership none and no diagnostic decision.

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
NETWORK = os.path.join(HERE, 'fixtures', 'inventory-network.json')
CORE = os.path.join(HERE, '..', '..')
CHECK = os.path.join(CORE, 'iac-authoring', 'scripts', 'check_spec.py')
WRITE = os.path.join(CORE, 'iac-authoring', 'scripts', 'write_spec.py')
EXPORT = os.path.join(CORE, 'iac-authoring', 'scripts', 'export_decisions.py')


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

    def map_fixture(fixture):
        """(spec, text, decision document, check_spec output) of one fixture, or None when not written."""
        name = os.path.basename(fixture)
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'infra-spec.yaml')
            r = subprocess.run([sys.executable, MAP, fixture, '--stage', 'production', '--language', 'de', '--out', out],
                               capture_output=True, text=True)
            expect(r.returncode == 0, f"{name}: map_inventory.py writes the spec (exit {r.returncode}) {r.stdout[-300:]}{r.stderr[-300:]}")
            if r.returncode != 0:
                return None
            c = subprocess.run([sys.executable, CHECK, out], capture_output=True, text=True)
            expect(c.returncode == 0, f"{name}: check_spec.py passes {c.stdout[-500:] if c.returncode else ''}")
            w = subprocess.run([sys.executable, WRITE, out, '--check', '--no-stamp'], capture_output=True, text=True)
            expect(w.returncode == 0, f"{name}: the spec is canonical")
            with open(out, encoding='utf-8') as f:
                text = f.read()
            md = os.path.join(tmp, 'infra-decisions.md')
            subprocess.run([sys.executable, EXPORT, out, '--out', md], capture_output=True, text=True)
            doc = open(md, encoding='utf-8').read() if os.path.isfile(md) else ''
            return yaml.safe_load(text), text, doc, c.stdout

    # ---------------------------------------------------------------- orders
    mapped = map_fixture(FIXTURE)
    if mapped is None:
        return 1
    spec, text, doc, _ = mapped
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
    expect(spec.get('deployment', {}).get('network_exposure') == {'value': 'public', 'source': 'imported'},
           'network_exposure follows from the public storage account')
    dep = spec.get('deployment', {})
    law = '/subscriptions/22222222-2222-2222-2222-222222222222/resourceGroups/rg-mgmt/providers/Microsoft.OperationalInsights/workspaces/law-central'
    expect(dep.get('observability_ownership', {}).get('value') == 'reference'
           and dep.get('diagnostics_destination', {}).get('value') == {'existing': 'log_analytics_workspace', 'id': {'production': law}},
           'the one workspace the settings write to is the deployment\'s destination, referenced')
    st_obs = st.get('observability', {})
    expect(st_obs.get('diagnostic_workspace', {}).get('source') == 'deployment'
           and st_obs.get('metrics_enabled') == {'value': True, 'source': 'imported'},
           'the storage account inherits the workspace and its metrics are read from its setting')
    app_obs = app.get('observability', {})
    expect(app_obs.get('diagnostic_workspace') == {'value': 'none', 'source': 'imported'}
           and 'metrics_enabled' not in app_obs and 'diagnostic_categories' not in app_obs,
           'the web app has no setting while another resource has one: workspace none, nothing else written')
    expect('## Abweichungen von den Vorgaben' in doc and '## Gefunden, nicht gebaut' in doc and 'dbw-orders' in doc,
           'the decision document lists the departures and what was not built')
    expect('NetworkWatcher' not in text and 'Failure Anomalies' not in text, 'the noise is left out')
    expect('hidden-link' not in text and spec['context'].get('tags') == {'owner_team': 'orders'},
           'tags Azure sets itself are left out, the shared one kept')

    # --------------------------------------------------------------- network
    mapped = map_fixture(NETWORK)
    if mapped is None:
        return 1
    spec, text, doc, checked = mapped
    res = spec.get('resources') or {}
    data = res.get('network-security-group__nsg-shop-data-gw-prod', {}).get('rules', {})
    rules = (data.get('rules') or {}).get('value') or []
    deny = next((x for x in rules if x.get('name') == 'Deny_Any_From_Internet'), {})
    expect(len(rules) == 4 and deny.get('access') == 'Deny' and deny.get('priority') == 4000
           and deny.get('source') == ['*'] and data.get('rules', {}).get('source') == 'imported',
           'every NSG rule is read as it runs, a Deny among them kept with its access')
    bootstrap = next((x for x in rules if x.get('name') == 'Allow_Any_From_Bootstrap_Network'), {})
    expect(bootstrap.get('source') == ['10.0.0.0/27'], "a rule's prefixes are merged from the singular and the plural field")
    expect(data.get('default_inbound') == {'value': 'azure_default', 'source': 'imported'},
           'no deny-all at 4096 reads as azure_default - a departure, not the default assumed')
    guarded = res.get('network-security-group__nsg-shop-data-gw-prod', {}).get('networking', {}).get('subnets', {})
    expect(guarded.get('value') == [{'resource': 'virtual-network', 'part': 'snet-shop-dataadditional-gw-prod'},
                                    {'resource': 'virtual-network', 'part': 'snet-shop-datape-gw-prod'}],
           'the subnets an NSG guards are the network\'s parts, in the network\'s spelling of an upper-case id')
    pe_subnet = res.get('key-vault', {}).get('networking', {}).get('private_endpoint_subnet', {})
    expect(pe_subnet == {'value': {'resource': 'virtual-network', 'part': 'snet-shop-datape-gw-prod'}, 'source': 'imported'},
           "the vault's endpoint subnet is read from its adopted private endpoint, as the network's part")
    expect('networkInterfaces' not in text and 'nic-shop-vault' not in text,
           "the private endpoint's network interface is noise, neither unmapped nor written")
    expect('has no network security group' not in checked, 'no subnet is reported without an NSG - all six have one')
    expect(spec.get('deployment', {}).get('observability_ownership') == {'value': 'none', 'source': 'imported'}
           and 'diagnostic_categories' not in text,
           'no diagnostic setting anywhere: ownership none, no diagnostic decision written')

    print('-' * 70)
    print('all passed' if not failures else f"{len(failures)} failed")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
