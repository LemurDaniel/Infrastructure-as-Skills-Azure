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

tests/fixtures/inventory-chat.json is a real chat app, anonymised and cut to a few rows: a private
vault, a public workspace, a private DNS zone with its network link, a web app on its plan, and
the action group Azure creates beside Application Insights. Its spec must:
  - read the workload from the adopted names through the convention, not from the group's name;
  - read the zone's name and its links (adopted as the zone's parts: children below its id);
  - make the zones the deployment's, and a private vault beside a public workspace
    private_with_exceptions with the workspace named, never public;
  - read the plan's size and OS from the plan's row, and count the action group as noise;
  - read the app's access, ranges, TLS, FTPS and health check from config/web and basic auth from
    the scm policy (children the fixture carries), and draw the app's role on the vault as an
    access line; keep the group's spelling (Import-Group).

Usage:
    python3 run_map_inventory_tests.py

Needs PyYAML. Exit 0 all pass, 1 a test failed, 2 could not run.
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = os.path.join(HERE, '..', 'scripts', 'map_inventory.py')
FIXTURE = os.path.join(HERE, 'fixtures', 'inventory-orders.json')
NETWORK = os.path.join(HERE, 'fixtures', 'inventory-network.json')
CHAT = os.path.join(HERE, 'fixtures', 'inventory-chat.json')
CORE = os.path.join(HERE, '..', '..')
CHECK = os.path.join(CORE, 'iac-authoring', 'scripts', 'check_spec.py')
WRITE = os.path.join(CORE, 'iac-authoring', 'scripts', 'write_spec.py')
EXPORT = os.path.join(CORE, 'iac-authoring', 'scripts', 'export_decisions.py')
DRAW = os.path.join(CORE, 'iac-diagram', 'scripts', 'new_diagram.py')


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
    dp = {k: (v or {}).get('value') for k, v in st.get('data_protection', {}).items()}
    expect(dp.get('blob_soft_delete_days') == 7 and dp.get('container_soft_delete_days') == 0
           and dp.get('versioning_enabled') is True and dp.get('change_feed_enabled') is False
           and dp.get('point_in_time_restore_days') == 0
           and st['data_protection']['blob_soft_delete_days'].get('source') == 'imported',
           'the blob service is read from its child: 7 days, a disabled policy as 0, absent settings as their missing answer')
    expect(st.get('networking', {}).get('firewall_ip_rules') == {'value': [], 'source': 'imported'},
           'no network ACL rules read as an empty list')
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
    listed = res.get('virtual-network', {}).get('addressing', {}).get('subnets', {}).get('value') or []
    expect(listed and all(s.get('azure_name') == s.get('name') for s in listed),
           'an adopted subnet keeps its deployed name as azure_name, so the render does not rename it')
    pe_subnet = res.get('key-vault', {}).get('networking', {}).get('private_endpoint_subnet', {})
    expect(pe_subnet == {'value': {'resource': 'virtual-network', 'part': 'snet-shop-datape-gw-prod'}, 'source': 'imported'},
           "the vault's endpoint subnet is read from its adopted private endpoint, as the network's part")
    expect('networkInterfaces' not in text and 'nic-shop-vault' not in text,
           "the private endpoint's network interface is noise, neither unmapped nor written")
    expect('has no network security group' not in checked, 'no subnet is reported without an NSG - all six have one')
    expect(spec.get('deployment', {}).get('observability_ownership') == {'value': 'none', 'source': 'imported'}
           and 'diagnostic_categories' not in text,
           'no diagnostic setting anywhere: ownership none, no diagnostic decision written')

    # ------------------------------------------------------------------ chat
    mapped = map_fixture(CHAT)
    if mapped is None:
        return 1
    spec, text, _, _ = mapped
    res, dep = spec.get('resources', {}), spec.get('deployment', {})
    expect(spec.get('context', {}).get('workload') == 'chat',
           "the workload is read from the adopted names (kv-sdc-prod-chat-...), not from the group Import-Group")
    zone = res.get('private-dns-zone', {})  # the one zone, so no instance suffix
    expect(zone.get('zone', {}).get('zone_names', {}).get('value') == ['privatelink.vaultcore.azure.net'],
           "a private DNS zone's name is read as its zone_names")
    expect(zone.get('networking', {}).get('vnet_links', {}).get('value') == [{'resource': 'virtual-network'}]
           and zone.get('networking', {}).get('resolution_policy', {}).get('value') == 'Default',
           'the virtual network links are read from the adopted links, the network as a reference')
    links = (zone.get('adopt', {}).get('parts', {}).get('value') or {}).get('production') or []
    expect(len(links) == 1 and '/virtualNetworkLinks/' in links[0] and 'virtualnetworklinks' not in str(spec.get('unmapped', '')).lower(),
           'a link is adopted as its zone\'s part - a child found by its id below the zone - not left unmapped')
    expect(dep.get('private_dns_ownership', {}).get('value') == 'deployment', 'an adopted zone makes the zones the deployment\'s')
    expect(dep.get('network_exposure', {}).get('value') == 'private_with_exceptions'
           and dep.get('public_parts', {}).get('value') == ['app-service', 'log-analytics-workspace'],
           'a private vault beside a public app and workspace is private with those as the exceptions, never public')
    app = res.get('app-service', {})
    expect(app.get('networking', {}).get('public_network_access', {}).get('value') == 'enabled_with_firewall'
           and app.get('networking', {}).get('ip_restrictions', {}).get('value') == ['203.0.113.5/32'],
           "the app's access and its allowed ranges are read from config/web, the Deny all entry left out")
    expect(app.get('security', {}).get('min_tls_version', {}).get('value') == '1.2'
           and app.get('security', {}).get('ftps_state', {}).get('value') == 'Disabled'
           and app.get('security', {}).get('basic_auth_enabled', {}).get('value') is False
           and app.get('runtime', {}).get('health_check_path', {}).get('value') == '/health',
           "TLS, FTPS, health check (config/web) and basic auth (the scm policy) are read, not assumed")
    expect(spec.get('wiring', {}).get('access', {}).get('value') == [{'from': 'app-service', 'to': 'key-vault', 'label': 'Key Vault Secrets User'}],
           'a role assignment between two adopted resources is an access line, labelled with the role')
    expect(spec.get('context', {}).get('resource_group_name') == {'production': 'Import-Group'},
           "the group keeps Azure's spelling, not the Resource Graph row's lower case")

    # The picture of an imported spec: endpoints from adopt.parts, adopted zones as zones,
    # adopted resources by their Azure names, the decisions in words.
    with tempfile.TemporaryDirectory() as tmp:
        spec_path, drawio = os.path.join(tmp, 'infra-spec.yaml'), os.path.join(tmp, 'd.drawio')
        with open(spec_path, 'w', encoding='utf-8') as f:
            f.write(text)
        d = subprocess.run([sys.executable, DRAW, spec_path, '--out', drawio], capture_output=True, text=True)
        xml = open(drawio, encoding='utf-8').read() if os.path.isfile(drawio) else ''
    # The fixture adopts no private endpoint: the plan and the zone's link are parts, no endpoint,
    # and a private posture alone does not draw one for an adopted resource.
    expect(d.returncode == 0 and not re.search(r'\d+× (AI Foundry|Key Vault|App Service|Private)', xml),
           f"no endpoint tile: an adopted resource has the endpoints adopt.parts holds, none here {d.stdout[-200:]}")
    expect('1× privatelink.*' in xml and 'privatelink-vaultcore' not in xml,
           'an adopted zone is drawn in the name-resolution area, not as a service')
    expect('kv-sdc-prod-chat-jaa' in xml and 'log-sdc-prod-chat-01' in xml,
           'adopted resources are named by their Azure names')
    expect('Ausnahme App Service, Log Analytics Workspace' in xml and 'Zonen in diesem Deployment' in xml
           and 'private_with_exceptions' not in xml,
           'the decisions panel says the exposure and the zone ownership in words')
    hosting = res.get('app-service', {}).get('hosting', {})
    expect(hosting.get('sku', {}).get('value') == 'P1v3' and hosting.get('os_type', {}).get('value') == 'Linux',
           "the App Service plan's size and OS are read from the adopted plan's row")
    expect('action-group' not in res and 'Smart Detection' not in text,
           'the action group Azure creates beside Application Insights is noise')

    print('-' * 70)
    print('all passed' if not failures else f"{len(failures)} failed")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
