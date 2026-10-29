#!/usr/bin/env python3
"""Tests for the resource-group and deployer-role rules of scripts/check_spec.py.

tests/fixtures/resource-groups.yaml is a valid spec with a split. It must pass clean; so must
the same spec with the split taken out (one group stays valid), split by lifecycle instead of
by concern, and without
`deployer_roles` (an older spec: a warning, not an error). Then each mutation breaks one rule
in a copy - a role that does not exist, a mode missing, a placement into a group the deployment
does not have, a deployer role the spec needs and does not grant, a `forced_by` naming a key the spec does not
have - and the check must fail with the message that names it. The same holds for a Foundry account in another region than
`context.location`: valid as stated, broken by a region nobody named, a missing reason, a
region per stage, another resource departing, or country residency. Application monitoring
enabled with an app and no application-insights resource fails; with the component it passes.
`observability_ownership: create` without a log-analytics-workspace resource fails, and so does
the workspace written as `{}`. An access line with a key other than from, to and label (an
unquoted comma in the label) or without its target fails, and so does an enum value outside its
question's `accepts`, on a resource and on the deployment, and a resource key that is no
question of its set, sits in another group, or sits directly under the resource. A mutation whose text is no
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
SCHEME_LIFECYCLE = "  resource_group_scheme: { value: lifecycle, source: asked }\n"
SCOPE_RG = "  deployment_scope: { value: resource_group, source: asked }\n"
ISOLATION_RG ="  stage_isolation: { value: resource_group, source: asked }\n"
GRANT_SUB = "      - { role: Contributor, scope: subscription, for: [deployment.resource_group_mode_main] }\n"
GRANT_RBAC = "      - { role: Role Based Access Control Administrator, scope: resource_group, for: [resources.key-vault] }\n"
GRANT_KV = "      - { role: Key Vault Secrets Officer, scope: key-vault, for: [resources.key-vault.security.secret_placeholders] }\n"
LOCAL_AUTH_LINE = "  local_auth: { value: disabled, source: default }\n"
MONITORING = "  application_monitoring: { value: enabled, source: default }\n"
WORKSPACE = "  log-analytics-workspace:\n    cost:\n      retention_days: { value: 30, source: default }\n"

# (name, find, replace, expected substring of the output; None = must pass)
MUTATIONS = [
    ('the split names main', SPLIT, "  resource_group_split: { value: [main, network, data, observability], source: stated }\n", "lists 'main'"),
    ('the split names a role that does not exist', SPLIT, "  resource_group_split: { value: [network, data, observability, frontend], source: stated }\n", "'frontend', which is not a role of the concern scheme"),
    ('the split names a role twice', SPLIT, "  resource_group_split: { value: [network, data, data, observability], source: stated }\n", 'twice'),
    ('the split is not a list', SPLIT, "  resource_group_split: { value: network, source: stated }\n", 'not a list of roles'),
    ('a split role has no mode', MODE_DATA, '', 'resource_group_mode_data is missing'),
    ('the main group has no mode', "  resource_group_mode_main: { value: create, source: stated }\n", '', 'resource_group_mode_main is missing'),
    ('a mode that is neither existing nor create', MODE_DATA, "  resource_group_mode_data: { value: destroy, source: stated }\n", "is not existing or create"),
    ('a mode for a role that is not split off', MODE_DATA, MODE_DATA + "  resource_group_mode_security: { value: create, source: stated }\n", 'resource_group_mode_security is stale'),
    ('a name for a role that is not split off', "  resource_group_name_network:\n", "  resource_group_name_security:\n    production: rg-sec-prod-we\n  resource_group_name_network:\n", 'resource_group_name_security is stale'),
    ('a placement into a role that is not split off', 'resource_group: { value: data,', 'resource_group: { value: security,', 'names a group the deployment does not have'),
    ('a placement into a group that does not exist', 'resource_group: { value: data,', 'resource_group: { value: frontend,', 'names a group the deployment does not have'),
    ('forced_by names a key the spec does not have', 'forced_by: deployment.address_space }', 'forced_by: deployment.adress_space }', "forced_by 'deployment.adress_space', which is neither a key in this spec"),
    ('forced_by lists a key the spec does not have', 'resources.key-vault.identity.role_assignments,', 'resources.key-vault.identity.role_asignments,', "forced_by 'resources.key-vault.identity.role_asignments'"),
    ('a placement without its reason', ', reason: the vault is kept with the data it protects', '', 'overridden with no reason'),
    ('a lock value that does not exist', "  resource_group_lock: { value: production, source: default }\n", "  resource_group_lock: { value: forever, source: default }\n", "resource_group_lock 'forever'"),
    ('a resource lock value that does not exist', "  resource_group_lock: { value: production, source: default }\n", "  resource_group_lock: { value: production, source: default }\n  resource_lock: { value: forever, source: default }\n", "resource_lock 'forever'"),
    ('a created group without Contributor on the subscription', GRANT_SUB, '', 'no Contributor on subscription'),
    ('a created group with Contributor on the group only', GRANT_SUB, GRANT_SUB.replace('subscription,', 'resource_group,'), 'no Contributor on subscription'),
    ('a role assignment without the role to assign it', GRANT_RBAC, '', 'no Role Based Access Control Administrator'),
    ('a secret placeholder without the role to write it', GRANT_KV, '', 'no Key Vault Secrets Officer'),
    ('the secrets role on another vault', GRANT_KV, GRANT_KV.replace('scope: key-vault,', 'scope: key-vault__other,'), 'no Key Vault Secrets Officer'),
    ('a grant without a scope', GRANT_KV, GRANT_KV.replace(' scope: key-vault,', ''), 'not a list of { role, scope, for }'),
    ('a concern role under the lifecycle scheme', SPLIT, SPLIT + SCHEME_LIFECYCLE, "'network', which is not a role of the lifecycle scheme"),
    ('a split under a single layout', SPLIT, SPLIT + "  resource_group_layout: { value: single, source: asked }\n", 'resource_group_layout is single'),
    ('a created group under resource-group stage isolation', MODE_DATA, MODE_DATA + ISOLATION_RG, 'resource_group_mode_data is create under stage_isolation resource_group'),
    ('a subscription grant under resource-group stage isolation', MODE_DATA, MODE_DATA + ISOLATION_RG, 'grants Contributor on subscription under stage_isolation'),
    ('a role granted to an identity the spec does not have', "            - { principal: app-service, role: Key Vault Secrets User }\n",
     "            - { principal: user-assigned-identity__gone, role: Key Vault Secrets User }\n", "'user-assigned-identity__gone', which is not a resource"),
    ('a created group at resource-group scope', MODE_DATA, MODE_DATA + SCOPE_RG, 'resource_group_mode_data is create under deployment_scope resource_group'),
    ('subscription scope under resource-group stage isolation', MODE_DATA,
     MODE_DATA + ISOLATION_RG + SCOPE_RG.replace('resource_group,', 'subscription,'), 'deployment_scope is subscription under stage_isolation'),
    ('application monitoring with an app and no component', LOCAL_AUTH_LINE, LOCAL_AUTH_LINE + MONITORING, 'but no application-insights resource'),
    ('a created workspace that is no resource', WORKSPACE, '',
     'but the spec has no log-analytics-workspace resource'),
    ('a created workspace with no decisions', WORKSPACE, "  log-analytics-workspace: {}\n",
     'resources.log-analytics-workspace records no decision'),
    ('an access label with an unquoted comma', 'label: HTTPS 443 }', 'label: Users, HTTPS 443 }',
     "wiring.access[0] (users -> app-service) has unknown key(s) HTTPS 443"),
    ('an access line without its target', '{ from: app-service, to: key-vault }', '{ from: app-service }',
     "wiring.access[2] has no 'to'"),
    ('an enum value its question does not accept', "  storage-account:\n    networking:\n      public_network_access: { value: disabled,",
     "  storage-account:\n    networking:\n      public_network_access: { value: firewalled,",
     "resources.storage-account.networking.public_network_access is 'firewalled', which is not one of its question's accepts"),
    ('a resource key its set does not ask', "  storage-account:\n    networking:\n",
     "  storage-account:\n    placement:\n      hierarchical_storage: { value: true, source: stated }\n    networking:\n",
     "resources.storage-account.placement.hierarchical_storage names no question of the storage-account set"),
    ('a question in the wrong group', "  storage-account:\n    networking:\n",
     "  storage-account:\n    security:\n      replication: { value: LRS, source: stated }\n    networking:\n",
     "resources.storage-account.security.replication is in group 'security', but the storage-account set asks replication in 'data_protection'"),
    ('a decision directly under a resource', "  storage-account:\n    networking:\n",
     "  storage-account:\n    storage_kind: { value: data_lake, source: stated }\n    networking:\n",
     "resources.storage-account.storage_kind is not resources.<resource>.<group>.<question>"),
    ('a deployment value its question does not accept', "  resource_group_lock: { value: production, source: default }\n",
     "  resource_group_lock: { value: production, source: default }\n  observability_ownership: { value: central, source: stated }\n",
     "deployment.observability_ownership is 'central', which is not one of its question's accepts"),
]

# The fixture with application monitoring and its component: (find, replace), both must hit.
WITH_COMPONENT = [
    (LOCAL_AUTH_LINE, LOCAL_AUTH_LINE + MONITORING),
    ("  log-analytics-workspace:\n", "  application-insights:\n    networking:\n      public_network_access: { value: enabled, source: default }\n  log-analytics-workspace:\n"),
]

# The fixture with a Foundry account in another region than context.location: valid, and
# each mutation breaks one rule of placement.location.
FOUNDRY_LOCATION = "      location: { value: swedencentral, source: stated, reason: gpt-4.1 as DataZoneStandard is not offered in westeurope }\n"
FOUNDRY = "  foundry:\n    placement:\n" + FOUNDRY_LOCATION
LAW = "  log-analytics-workspace:\n"
LOCAL_AUTH = "  local_auth: { value: disabled, source: default }\n"
FOUNDRY_MUTATIONS = [
    ('another region for a resource that is not the Foundry account', "  storage-account:\n",
     "  storage-account:\n    placement:\n" + FOUNDRY_LOCATION, 'only the Foundry account departs'),
    ('a region the run picked', 'source: stated, reason: gpt', 'source: assumed, reason: gpt', 'is assumed - a region nobody named'),
    ('a region without its reason', ', reason: gpt-4.1 as DataZoneStandard is not offered in westeurope', '', 'carries no reason'),
    ('a departure into context.location', 'value: swedencentral', 'value: westeurope', 'is context.location (westeurope)'),
    ('a region per stage', 'value: swedencentral', 'value: { production: swedencentral }', 'is not one region'),
    ('another region under country residency', LOCAL_AUTH, LOCAL_AUTH + "  data_residency: { value: country, source: asked }\n",
     'under data_residency country'),
]

# The same split by lifecycle: (find, replace) in order, every one must hit.
LIFECYCLE = [
    (SPLIT, "  resource_group_split: { value: [foundation, state], source: forced, forced_by: deployment.resource_group_scheme }\n" + SCHEME_LIFECYCLE),
    ("  resource_group_mode_network: { value: existing, source: stated }\n", "  resource_group_mode_foundation: { value: existing, source: stated }\n"),
    (MODE_DATA, "  resource_group_mode_state: { value: create, source: stated }\n"),
    ("  resource_group_mode_observability: { value: create, source: asked }\n", ''),
    ("  resource_group_name_network:\n", "  resource_group_name_foundation:\n"),
    ('resource_group: { value: data,', 'resource_group: { value: state,'),
]

# The same split under resource_group_layout split: no main group, application gets its own.
SPLIT_NO_MAIN = ("  resource_group_layout: { value: split, source: asked }\n"
                 "  resource_group_scheme: { value: concern, source: asked }\n"
                 "  resource_group_split: { value: [network, data, application, observability], source: forced, forced_by: deployment.resource_group_scheme }\n")
MODE_MAIN = "  resource_group_mode_main: { value: create, source: stated }\n"
NAME_MAIN = "  resource_group_name:\n    production: rg-shop-prod-we\n"
NO_MAIN = [
    (SPLIT, SPLIT_NO_MAIN),
    (MODE_MAIN, "  resource_group_mode_application: { value: create, source: stated }\n"),
    (NAME_MAIN, ''),
]
# (name, find, replace, expected) applied to the no-main variant
NO_MAIN_MUTATIONS = [
    ('a main group mode under a split', MODE_DATA, MODE_DATA + MODE_MAIN, 'resource_group_mode_main is stale'),
    ('a main group name under a split', "  resource_group_name_network:\n", NAME_MAIN + "  resource_group_name_network:\n", 'context.resource_group_name is stale'),
    ('a resource whose role is not split off, with no main to fall into', SPLIT_NO_MAIN,
     SPLIT_NO_MAIN.replace('[network, data, application, observability]', '[network, data, observability]'),
     "resources.app-service belongs to 'application'"),
    ('a split with no roles', SPLIT_NO_MAIN, SPLIT_NO_MAIN.replace('[network, data, application, observability]', '[]'), 'is empty under resource_group_layout split'),
]

# The no-main variant split by part of the system: the network and the workspace are shared,
# the rest is the part `shop`, each resource placed in it.
PLACE_APP = "  app-service:\n    placement:\n      resource_group: { value: shop, source: forced, forced_by: wiring.purposes }\n"
COMPONENT = [
    (SPLIT_NO_MAIN, "  resource_group_layout: { value: split, source: asked }\n"
                    "  resource_group_scheme: { value: component, source: asked }\n"
                    "  resource_group_components: { value: [shop], source: forced, forced_by: wiring.purposes }\n"
                    "  resource_group_split: { value: [shared, shop], source: forced, forced_by: deployment.resource_group_scheme }\n"),
    ("  resource_group_mode_application: { value: create, source: stated }\n", "  resource_group_mode_shop: { value: create, source: stated }\n"),
    ("  resource_group_mode_network: { value: existing, source: stated }\n", "  resource_group_mode_shared: { value: existing, source: stated }\n"),
    (MODE_DATA, ''),
    ("  resource_group_mode_observability: { value: create, source: asked }\n", ''),
    ("  resource_group_name_network:\n", "  resource_group_name_shared:\n"),
    ('resource_group: { value: data,', 'resource_group: { value: shop,'),
    ("  app-service:\n", PLACE_APP),
    ("  storage-account:\n", "  storage-account:\n    placement:\n      resource_group: { value: shop, source: forced, forced_by: wiring.purposes }\n"),
]
COMPONENT_MUTATIONS = [
    ('a resource with no part under the component scheme', PLACE_APP, "  app-service:\n", 'resources.app-service names no part'),
    ('a placement into a part that is not named', PLACE_APP, PLACE_APP.replace('value: shop,', 'value: admin,'), 'names a group the deployment does not have'),
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

    text = base
    for find, replace in LIFECYCLE:
        if text.count(find) != 1:
            report(False, 'a split by lifecycle stays valid', f"the fixture no longer holds once: {find!r}")
            break
        text = text.replace(find, replace)
    else:
        rc, out = run(text)
        report(rc == 0 and 'main and 2 split role(s)' in out, 'a split by lifecycle stays valid', out[-400:])

    no_main = base
    for find, replace in NO_MAIN:
        if no_main.count(find) != 1:
            report(False, 'a split without a main group stays valid', f"the fixture no longer holds once: {find!r}")
            no_main = None
            break
        no_main = no_main.replace(find, replace)
    if no_main is not None:
        rc, out = run(no_main)
        report(rc == 0 and 'no main group, 4 split role(s)' in out, 'a split without a main group stays valid', out[-400:])
        for name, find, replace, expected in NO_MAIN_MUTATIONS:
            if no_main.count(find) != 1:
                report(False, name, f"the mutation text is in the variant {no_main.count(find)} times: {find[:60]!r}")
                continue
            rc, out = run(no_main.replace(find, replace))
            report(rc == 1 and expected in out, f"breaks: {name}", f"expected exit 1 with {expected!r}; got exit {rc}:\n{out[-500:]}")

        component = no_main
        for find, replace in COMPONENT:
            if component.count(find) != 1:
                report(False, 'a split by part of the system stays valid', f"the variant no longer holds once: {find!r}")
                component = None
                break
            component = component.replace(find, replace)
        if component is not None:
            rc, out = run(component)
            report(rc == 0 and 'no main group, 2 split role(s), 3 placement(s)' in out, 'a split by part of the system stays valid', out[-400:])
            for name, find, replace, expected in COMPONENT_MUTATIONS:
                if component.count(find) != 1:
                    report(False, name, f"the mutation text is in the variant {component.count(find)} times: {find[:60]!r}")
                    continue
                rc, out = run(component.replace(find, replace))
                report(rc == 1 and expected in out, f"breaks: {name}", f"expected exit 1 with {expected!r}; got exit {rc}:\n{out[-500:]}")

    start, end = base.find('  deployer_roles:\n'), base.find('    forced_by: [deployment.resource_group_mode_main')
    if start < 0 or end < 0:
        report(False, 'an older spec without deployer_roles stays valid', 'the fixture no longer holds the deployer_roles block')
    else:
        rc, out = run(base[:start] + base[base.index('\n', end) + 1:])
        report(rc == 0 and 'deployer_roles is missing' in out, 'an older spec without deployer_roles stays valid, with a warning', out[-400:])

    if base.count(LAW) != 1:
        report(False, 'a Foundry account in another region stays valid', f"the fixture no longer holds once: {LAW!r}")
    else:
        foundry = base.replace(LAW, FOUNDRY + LAW)
        rc, out = run(foundry)
        report(rc == 0, 'a Foundry account in another region stays valid', out[-400:])
        for name, find, replace, expected in FOUNDRY_MUTATIONS:
            if foundry.count(find) != 1:
                report(False, name, f"the mutation text is in the variant {foundry.count(find)} times: {find[:60]!r}")
                continue
            rc, out = run(foundry.replace(find, replace))
            report(rc == 1 and expected in out, f"breaks: {name}", f"expected exit 1 with {expected!r}; got exit {rc}:\n{out[-500:]}")

    for name, find, replace, expected in MUTATIONS:
        if base.count(find) != 1:
            report(False, name, f"the mutation text is in the fixture {base.count(find)} times: {find[:60]!r}")
            continue
        rc, out = run(base.replace(find, replace))
        report(rc == 1 and expected in out, f"breaks: {name}", f"expected exit 1 with {expected!r}; got exit {rc}:\n{out[-500:]}")

    text = base
    for find, replace in WITH_COMPONENT:
        if text.count(find) != 1:
            report(False, 'application monitoring with its component stays valid', f"the fixture no longer holds once: {find!r}")
            break
        text = text.replace(find, replace)
    else:
        rc, out = run(text)
        report(rc == 0, 'application monitoring with its component stays valid', out[-400:])

    print('-' * 70)
    total = 7 + len(MUTATIONS) + len(NO_MAIN_MUTATIONS) + len(COMPONENT_MUTATIONS)
    print(f"{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
