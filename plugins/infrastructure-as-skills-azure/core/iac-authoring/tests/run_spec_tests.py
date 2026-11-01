#!/usr/bin/env python3
"""Tests for the resource-group and deployer-role rules of scripts/check_spec.py.

tests/fixtures/resource-groups.yaml is a valid spec with a split, no main group, its groups
derived from the scheme and the placements. It must pass clean; so must the same spec with the
split taken out (one group stays valid), split by lifecycle or by part of the system instead of
by concern, and without
`deployer_roles` (an older spec: a warning, not an error). Then each mutation breaks one rule
in a copy - a group list written down, a mode missing, a placement into a role the scheme does
not have, a deployer role the spec needs and does not grant, a `forced_by` naming a key the spec does not
have - and the check must fail with the message that names it. The same holds for a Foundry account in another region than
`context.location`: valid as stated, broken by a region nobody named, a missing reason, a
region per stage, another resource departing, or country residency. Application monitoring
enabled with an app and no application-insights resource fails; with the component it passes.
`observability_ownership: create` without a log-analytics-workspace resource fails, and so does
the workspace written as `{}`. An access line with a key other than from, to and label (an
unquoted comma in the label) or without its target fails, and so does an enum value outside its
question's `accepts`, on a resource and on the deployment, and a resource key that is no
question of its set, sits in another group, or sits directly under the resource. A mutation whose text is no
longer in the fixture fails the run: a test that cannot break anything proves nothing. Last, the
Shape example of references/spec.md must pass the check and be in write_spec.py's canonical form,
so the reference cannot show a spec the plugin would refuse. On it, a per_environment range or
reference object written as one value fails, and so does every broken reference: a bare name,
a stage map, a resource of another kind or not in the spec, a subnet without its part or with
one the network does not name, an existing one with no id and no open entry, an id of another
type, a stage without an id, a name beside it. An existing one with its ids, or with an open
entry, passes.

tests/fixtures/imported.yaml is a spec as an import (iac-unclick) writes it: adopted resources
with the ids of their lock and diagnostic setting, adopted role assignments, unmapped items and
spec.imported_from. It must pass and be canonical; each mutation breaks one rule of
scripts/spec_import.py - an id of another type, a lock under another resource, an id as one value
or defaulted, a key the adopt group does not have, a resource that records nothing but its id, a
role assignment id that is none, an unmapped entry with an unknown reason or an id of another
type, a scope that is no scope, no read_at.

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
WRITE = os.path.join(HERE, '..', 'scripts', 'write_spec.py')
SPEC_MD = os.path.join(HERE, '..', 'references', 'spec.md')
FIXTURE = os.path.join(HERE, 'fixtures', 'resource-groups.yaml')
IMPORTED = os.path.join(HERE, 'fixtures', 'imported.yaml')

LAYOUT = "  resource_group_layout: { value: split, source: asked }\n"
SCHEME = "  resource_group_scheme: { value: concern, source: asked }\n"
CREATED = "  resource_groups_created: { value: [application, data, observability], source: stated }\n"
NAME_MAIN = "  resource_group_name:\n    production: rg-shop-prod-we\n"
SCHEME_LIFECYCLE = "  resource_group_scheme: { value: lifecycle, source: asked }\n"
SCOPE_RG = "  deployment_scope: { value: resource_group, source: asked }\n"
ISOLATION_RG ="  stage_isolation: { value: resource_group, source: asked }\n"
GRANT_SUB = "      - { role: Contributor, scope: subscription, for: [deployment.resource_groups_created] }\n"
GRANT_RBAC = "      - { role: Role Based Access Control Administrator, scope: resource_group, for: [resources.key-vault] }\n"
GRANT_KV = "      - { role: Key Vault Secrets Officer, scope: key-vault, for: [resources.key-vault.security.secret_placeholders] }\n"
LOCAL_AUTH_LINE = "  local_auth: { value: disabled, source: default }\n"
MONITORING = "  application_monitoring: { value: enabled, source: default }\n"
WORKSPACE = "  log-analytics-workspace:\n    cost:\n      retention_days: { value: 30, source: default }\n"

# On the Shape example of spec.md, which has three stages: a per_environment value outside the
# spec must be a stage map; one that names only what the spec defines stays one value.
SHAPE_RANGES = "    value:\n      development: 10.42.0.0/24\n      test: 10.43.0.0/24\n      production: 10.44.0.0/24\n    source: asked\n"
SHAPE_MUTATIONS = [
    ('a per_environment range as one value', SHAPE_RANGES, "    value: 10.42.0.0/24\n    source: asked\n",
     'deployment.address_space is one value, but its question is per_environment'),
]

# References (spec_ref.py): on the Shape example's integration subnet and a workspace outside it.
SHAPE_SUBNET = "        value:  # a reference: a part of a resource of this spec, the same in every stage\n          resource: virtual-network\n          part: snet-app\n"
LAW = "  diagnostics_destination:\n    value:\n      existing: log_analytics_workspace\n"
LAW_ID = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-platform/providers/Microsoft.OperationalInsights/workspaces/law-platform"
LAW_IDS = "".join(f"        {s}: {LAW_ID}\n" for s in ('development', 'test', 'production'))
SHAPE_MUTATIONS += [
    ('a name and resource group instead of a reference', SHAPE_RANGES,
     SHAPE_RANGES + "  diagnostics_destination: {value: {name: law-platform, resource_group_name: rg-platform}, source: stated}\n",
     "deployment.diagnostics_destination holds {'name': 'law-platform'"),
    ('a bare subnet name', SHAPE_SUBNET, "        value: snet-app\n", "integration_subnet holds 'snet-app', which is no reference"),
    ('a reference split by stage', SHAPE_SUBNET,
     "        value:\n          development: {resource: virtual-network, part: snet-app}\n"
     "          test: {resource: virtual-network, part: snet-app}\n          production: {resource: virtual-network, part: snet-app}\n",
     'integration_subnet is a reference split by stage'),
    ('a resource of another kind', SHAPE_SUBNET, "        value:\n          resource: storage-account\n",
     "references 'storage-account', which is no subnet"),
    ('a subnet without its part', SHAPE_SUBNET, "        value:\n          resource: virtual-network\n", 'without part'),
    ('a part the network does not name', SHAPE_SUBNET, SHAPE_SUBNET.replace('part: snet-app', 'part: snet-gone'),
     "part 'snet-gone' of 'virtual-network', which its addressing.subnets does not name"),
    ('a resource the spec does not hold', SHAPE_SUBNET, SHAPE_SUBNET.replace('resource: virtual-network', 'resource: virtual-network__hub'),
     "references resource 'virtual-network__hub', which this spec does not hold"),
    ('an existing reference with no id and no open entry', SHAPE_RANGES, SHAPE_RANGES + LAW + "    source: stated\n",
     'with no id and no open entry'),
    ('an existing reference whose id is open', SHAPE_RANGES, SHAPE_RANGES + LAW + "    source: stated\n",
     None, "- key: deployment.diagnostics_destination\n  question: Welche Resource-ID hat der zentrale Workspace?\n  owner: Plattform-Team\n  blocks: apply\n"),
    ('an existing reference with an id per stage', SHAPE_RANGES, SHAPE_RANGES + LAW + "      id:\n" + LAW_IDS + "    source: stated\n", None),
    ('an existing reference with an id of another type', SHAPE_RANGES,
     SHAPE_RANGES + LAW + "      id:\n" + LAW_IDS.replace('Microsoft.OperationalInsights/workspaces', 'Microsoft.Storage/storageAccounts') + "    source: stated\n",
     'which is not the id of a Microsoft.OperationalInsights/workspaces'),
    ('an existing reference missing a stage', SHAPE_RANGES,
     SHAPE_RANGES + LAW + "      id:\n" + LAW_IDS.split('\n', 1)[1] + "    source: stated\n", "has no id for stage 'development'"),
    ('an existing reference with a name beside it', SHAPE_RANGES,
     SHAPE_RANGES + LAW + "      name: law-platform\n" + "    source: stated\n", 'never a name or a resource group'),
]

# The envelope and the escape hatch: a format this plugin does not know, an override without its reason.
OVERRIDE = "    _target_overrides:\n      terraform:\n        lifecycle_ignore:\n          value: [created_at]\n"
SHAPE_MUTATIONS += [
    ('a spec format newer than the plugin', "schema_version: 1\n", "schema_version: 2\n", 'a spec format newer than this plugin reads'),
    ('an override with its reason', "\n  key-vault:\n", "\n" + OVERRIDE + "          reason: azurerm sets the tag itself\n  key-vault:\n", None),
    ('an override without a reason', "\n  key-vault:\n", "\n" + OVERRIDE + "  key-vault:\n", 'lifecycle_ignore has no reason'),
    ('an override as a bare value', "\n  key-vault:\n", "\n    _target_overrides:\n      terraform:\n        lifecycle_ignore: [created_at]\n  key-vault:\n",
     'lifecycle_ignore is not { value, reason }'),
]

# NSGs on the Shape example, which guards snet-app and the implied private endpoint subnet
# `endpoints`: an association is exclusive (a subnet takes one NSG), and every subnet the spec
# creates has one. (name, [(find, replace)], expected; None = must pass)
def nsg(name):
    return (f"  network-security-group__{name}:\n    networking:\n      subnets:\n        value:\n"
            "        - resource: virtual-network\n          part: snet-app\n        source: stated\n")


SHAPE_MODULE = "    contains: [virtual-network, network-security-group__app, network-security-group__endpoints]\n"
SHAPE_NSG_ENDPOINTS = ("  network-security-group__endpoints:\n    networking:\n      subnets:\n        value:\n"
                       "        - resource: virtual-network\n"
                       "          part: endpoints  # the private endpoint subnet: no listed subnet carries its prefix\n"
                       "        source:\n          forced_by: resources.virtual-network.addressing.subnets\n"
                       "    rules:\n      subnet_purpose:\n        value: private_endpoints\n        source:\n"
                       "          forced_by: resources.virtual-network.addressing.private_endpoint_subnet_prefix\n\n")
SHAPE_EDITS = [
    ('a second NSG on a subnet', [("\n  app-service:\n", "\n" + nsg('a') + "  app-service:\n"),
                                  (SHAPE_MODULE, SHAPE_MODULE.replace(']', ', network-security-group__a]'))],
     'snet-app of virtual-network is claimed by 2 network-security-group resources'),
    ('a subnet without an NSG', [(SHAPE_NSG_ENDPOINTS, ''),
                                 (SHAPE_MODULE, SHAPE_MODULE.replace(', network-security-group__endpoints', ''))],
     'subnet endpoints of virtual-network has no network security group'),
    # Listed with the private endpoint prefix, the subnet is that one by its own name: no `endpoints`.
    ('the private endpoint subnet listed by name',
     [(f"          {s}:\n          - name: snet-app\n", f"          {s}:\n          - name: snet-pe\n            prefix: {p}\n          - name: snet-app\n")
      for s, p in (('development', '10.42.0.0/27'), ('test', '10.43.0.0/27'), ('production', '10.44.0.0/27'))]
     + [("          part: endpoints  # the private endpoint subnet: no listed subnet carries its prefix\n", "          part: snet-pe\n")],
     None),
]

# The fixture's storage account up to its first group: its meta comes first.
STORAGE = "  storage-account:\n    meta:\n      purpose: { value: Product images, source: stated }\n"

# (name, find, replace, expected substring of the output; None = must pass)
MUTATIONS = [
    ('a split list written down', LAYOUT, LAYOUT + "  resource_group_split: { value: [network, data], source: stated }\n",
     'deployment.resource_group_split is no longer written'),
    ('component parts written down', LAYOUT, LAYOUT + "  resource_group_components: { value: [shop], source: stated }\n",
     'deployment.resource_group_components is no longer written'),
    ('a mode written down', CREATED, CREATED + "  resource_group_mode_data: { value: create, source: stated }\n",
     'deployment.resource_group_mode_data is no longer written'),
    ('the created list is not a list', CREATED, "  resource_groups_created: { value: data, source: stated }\n", 'is not a list of groups'),
    ('a created group no resource is in', CREATED, CREATED.replace('observability]', 'observability, security]'),
     "resource_groups_created lists 'security', which has no group"),
    ('main created under a split', CREATED, CREATED.replace('[application,', '[main, application,'),
     "resource_groups_created lists 'main', which has no group (under a split there is no main group)"),
    ('a name for a role no resource is in', "  resource_group_name_network:\n", "  resource_group_name_security:\n    production: rg-sec-prod-we\n  resource_group_name_network:\n", 'resource_group_name_security is stale'),
    ('a placement into a role the scheme does not have', 'resource_group: { value: data,', 'resource_group: { value: frontend,', "'frontend' is not a role of the concern scheme"),
    ('a main group name under a split', "  resource_group_name_network:\n", NAME_MAIN + "  resource_group_name_network:\n", 'context.resource_group_name is stale'),
    ('a concern placement under the lifecycle scheme', SCHEME, SCHEME_LIFECYCLE, "'data' is not a role of the lifecycle scheme"),
    ('a scheme under a single layout', LAYOUT, "  resource_group_layout: { value: single, source: asked }\n", 'resource_group_scheme is stale'),
    ('forced_by names a key the spec does not have', 'forced_by: deployment.address_space }', 'forced_by: deployment.adress_space }', "forced_by 'deployment.adress_space', which is neither a key in this spec"),
    ('forced_by lists a key the spec does not have', 'resources.key-vault.identity.role_assignments,', 'resources.key-vault.identity.role_asignments,', "forced_by 'resources.key-vault.identity.role_asignments'"),
    ('a placement without its reason', 'source: { overridden: the vault is kept with the data it protects }', "source: { overridden: '' }", 'overridden with no reason'),
    ('a pointer beside its source', 'source: { overridden: the vault is kept with the data it protects }',
     'source: overridden, reason: the vault is kept with the data it protects', 'carries reason beside its source'),
    ('a forced value under the old word', 'source: { forced_by: deployment.address_space }',
     'source: forced, forced_by: deployment.address_space', "write source: {forced_by: ...}"),
    ('a lock value that does not exist', "  resource_group_lock: { value: production, source: default }\n", "  resource_group_lock: { value: forever, source: default }\n", "resource_group_lock 'forever'"),
    ('a resource lock value that does not exist', "  resource_group_lock: { value: production, source: default }\n", "  resource_group_lock: { value: production, source: default }\n  resource_lock: { value: forever, source: default }\n", "resource_lock 'forever'"),
    ('a created group without Contributor on the subscription', GRANT_SUB, '', 'no Contributor on subscription'),
    ('a created group with Contributor on the group only', GRANT_SUB, GRANT_SUB.replace('subscription,', 'resource_group,'), 'no Contributor on subscription'),
    ('a role assignment without the role to assign it', GRANT_RBAC, '', 'no Role Based Access Control Administrator'),
    ('a secret placeholder without the role to write it', GRANT_KV, '', 'no Key Vault Secrets Officer'),
    ('the secrets role on another vault', GRANT_KV, GRANT_KV.replace('scope: key-vault,', 'scope: key-vault__other,'), 'no Key Vault Secrets Officer'),
    ('a grant without a scope', GRANT_KV, GRANT_KV.replace(' scope: key-vault,', ''), 'not a list of { role, scope, for }'),
    ('a created group under resource-group stage isolation', CREATED, CREATED + ISOLATION_RG, "resource group 'application' is created (resource_groups_created) under stage_isolation resource_group"),
    ('a subscription grant under resource-group stage isolation', CREATED, CREATED + ISOLATION_RG, 'grants Contributor on subscription under stage_isolation'),
    ('a role granted to an identity the spec does not have', "            - { principal: app-service, role: Key Vault Secrets User }\n",
     "            - { principal: user-assigned-identity__gone, role: Key Vault Secrets User }\n", "'user-assigned-identity__gone', which is not a resource"),
    ('a created group at resource-group scope', CREATED, CREATED + SCOPE_RG, "resource group 'application' is created (resource_groups_created) under deployment_scope resource_group"),
    ('subscription scope under resource-group stage isolation', CREATED,
     CREATED + ISOLATION_RG + SCOPE_RG.replace('resource_group,', 'subscription,'), 'deployment_scope is subscription under stage_isolation'),
    ('application monitoring with an app and no component', LOCAL_AUTH_LINE, LOCAL_AUTH_LINE + MONITORING, 'but no application-insights resource'),
    ('a created workspace that is no resource', WORKSPACE, '',
     'but the spec has no log-analytics-workspace resource'),
    ('a created workspace with no decisions', WORKSPACE, "  log-analytics-workspace: {}\n",
     'resources.log-analytics-workspace records no decision'),
    ('an access label with an unquoted comma', 'label: HTTPS 443 }', 'label: Users, HTTPS 443 }',
     "wiring.access[0] (users -> app-service) has unknown key(s) HTTPS 443"),
    ('an access line without its target', '{ from: app-service, to: key-vault }', '{ from: app-service }',
     "wiring.access[2] has no 'to'"),
    ('an enum value its question does not accept', STORAGE + "    networking:\n      public_network_access: { value: disabled,",
     STORAGE + "    networking:\n      public_network_access: { value: firewalled,",
     "resources.storage-account.networking.public_network_access is 'firewalled', which is not one of its question's accepts"),
    ('a resource key its set does not ask', STORAGE + "    networking:\n",
     STORAGE + "    placement:\n      hierarchical_storage: { value: true, source: stated }\n    networking:\n",
     "resources.storage-account.placement.hierarchical_storage names no question of the storage-account set"),
    ('a question in the wrong group', STORAGE + "    networking:\n",
     STORAGE + "    security:\n      replication: { value: LRS, source: stated }\n    networking:\n",
     "resources.storage-account.security.replication is in group 'security', but the storage-account set asks replication in 'data_protection'"),
    ('a decision directly under a resource', STORAGE + "    networking:\n",
     STORAGE + "    storage_kind: { value: data_lake, source: stated }\n    networking:\n",
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
FOUNDRY_LOCATION = "      location: { value: swedencentral, source: { overridden: gpt-4.1 as DataZoneStandard is not offered in westeurope } }\n"
FOUNDRY = "  foundry:\n    placement:\n" + FOUNDRY_LOCATION
LAW = "  log-analytics-workspace:\n"
LOCAL_AUTH = "  local_auth: { value: disabled, source: default }\n"
FOUNDRY_MUTATIONS = [
    ('another region for a resource that is not the Foundry account', "  storage-account:\n",
     "  storage-account:\n    placement:\n" + FOUNDRY_LOCATION, 'only the Foundry account departs'),
    ('a region the run picked', 'source: { overridden: gpt-4.1 as DataZoneStandard is not offered in westeurope }', 'source: assumed', 'is assumed - a region apart from context.location'),
    ('a region without its reason', 'overridden: gpt-4.1 as DataZoneStandard is not offered in westeurope', "overridden: ''", 'carries no reason'),
    ('a departure into context.location', 'value: swedencentral', 'value: westeurope', 'is context.location (westeurope)'),
    ('a region per stage', 'value: swedencentral', 'value: { production: swedencentral }', 'is not one region'),
    ('another region under country residency', LOCAL_AUTH, LOCAL_AUTH + "  data_residency: { value: country, source: asked }\n",
     'under data_residency country'),
]

# The same split by lifecycle: (find, replace) in order, every one must hit.
LIFECYCLE = [
    (SCHEME, SCHEME_LIFECYCLE),
    (CREATED, "  resource_groups_created: { value: [runtime, state], source: stated }\n"),
    ("  resource_group_name_network:\n", "  resource_group_name_foundation:\n"),
    ('resource_group: { value: data,', 'resource_group: { value: state,'),
]

# The split by part of the system: the network and the workspace are shared, the rest is the
# part `shop`, each resource placed in it. The parts are the placements; nothing lists them.
PLACE_APP = "  app-service:\n    placement:\n      resource_group: { value: shop, source: { forced_by: meta.purpose } }\n"
COMPONENT = [
    (SCHEME, "  resource_group_scheme: { value: component, source: asked }\n"),
    (CREATED, "  resource_groups_created: { value: [shop], source: stated }\n"),
    ("  resource_group_name_network:\n", "  resource_group_name_shared:\n"),
    ('resource_group: { value: data,', 'resource_group: { value: shop,'),
    ("  app-service:\n", PLACE_APP),
    (STORAGE, STORAGE + "    placement:\n      resource_group: { value: shop, source: { forced_by: meta.purpose } }\n"),
]
COMPONENT_MUTATIONS = [
    ('a resource with no part under the component scheme', PLACE_APP, "  app-service:\n", 'resources.app-service names no part'),
    ('a part created that no resource is placed in', "  resource_groups_created: { value: [shop], source: stated }\n",
     "  resource_groups_created: { value: [shop, admin], source: stated }\n", "resource_groups_created lists 'admin', which has no group"),
]

# The same spec without a split: every resource group line and the placement taken out.
NO_SPLIT = [
    LAYOUT, SCHEME, CREATED,
    "  resource_group_lock: { value: production, source: default }\n",
    "  resource_group_name_network:\n    production: rg-spoke-shop-prod-we\n",
    "    placement:\n      resource_group: { value: data, source: { overridden: the vault is kept with the data it protects } }\n",
]

# An import (iac-unclick): tests/fixtures/imported.yaml must pass; each mutation breaks one rule
# of spec_import.py. (name, find, replace, expected message)
SUB = '/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-payments-prod/providers/'
STORAGE_ID = SUB + 'Microsoft.Storage/storageAccounts/stpaymentsprod01'
APP_ID = "          production: " + SUB + "Microsoft.Web/sites/app-payments-prod\n"
APP_DECISIONS = ("    hosting:\n      sku:\n        value: P1v3\n        source: imported\n"
                 "    identity:\n      managed_identity:\n        value: system_assigned\n        source: imported\n")
IMPORT_MUTATIONS = [
    ('an adopted id of another type', APP_ID, APP_ID.replace('Microsoft.Web/sites/', 'Microsoft.Web/serverFarms/'),
     'set creates a Microsoft.Web/sites'),
    ('a lock under another resource', STORAGE_ID + '/providers/Microsoft.Authorization/locks/nodelete',
     STORAGE_ID.replace('stpaymentsprod01', 'stother') + '/providers/Microsoft.Authorization/locks/nodelete',
     'which is no Microsoft.Authorization/locks of the adopted resource'),
    ('an adopted id as one value', "    adopt:\n      id:\n        value:\n" + APP_ID,
     "    adopt:\n      id:\n        value: " + APP_ID.strip().split(': ', 1)[1] + "\n",
     'adopt.id is not a map keyed by stage'),
    ('an adopted id defaulted', APP_ID + "        source: imported\n", APP_ID + "        source: default\n",
     'never defaulted or assumed'),
    ('a key the adopt group does not have', APP_ID + "        source: imported\n",
     APP_ID + "        source: imported\n      name:\n        value: app-payments-prod\n        source: imported\n",
     'adopt holds name'),
    ('a resource that records nothing but its id', APP_DECISIONS, '', 'resources.app-service records no decision'),
    ('a role assignment id that is none', 'roleAssignments/9f3c1a2b-0000-4000-8000-000000000001',
     'roleDefinitions/9f3c1a2b-0000-4000-8000-000000000001', 'which is no role assignment id'),
    ('an unmapped entry with an unknown reason', '  reason: no_question_set\n', '  reason: too_hard\n',
     "has reason 'too_hard'"),
    ('an unmapped id of another type', 'providers/Microsoft.Databricks/workspaces/dbw-payments',
     'providers/Microsoft.Web/sites/dbw-payments', 'which is no Microsoft.Databricks/workspaces'),
    ('a scope that is no scope', '  imported_from:\n    scopes: [/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/rg-payments-prod]\n',
     '  imported_from:\n    scopes: [rg-payments-prod]\n', 'no subscription or resource group id'),
    ('no read_at', '    read_at: 2026-11-01T09:58:12Z\n', '', 'spec.imported_from.read_at is not a UTC time'),
]


def run(text, cmd=None):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'infra-spec.yaml')
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
        script, *args = cmd or [CHECK]
        proc = subprocess.run([sys.executable, '-I', script, path, *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def shape_example():
    """The first ```yaml block under '## Shape' in references/spec.md, or None."""
    with open(SPEC_MD, encoding='utf-8') as f:
        text = f.read().replace('\r\n', '\n')
    start = text.find('\n## Shape\n')
    if start < 0:
        return None
    start = text.find('```yaml\n', start)
    end = text.find('\n```\n', start)
    if start < 0 or end < 0:
        return None
    return text[start + len('```yaml\n'):end + 1]


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
    report(rc == 0 and 'resource groups - no main group, 4 split role(s), 1 placement(s)' in out, 'the fixture passes', out[-400:])

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
        report(rc == 0 and 'no main group, 3 split role(s)' in out, 'a split by lifecycle stays valid', out[-400:])

    component = base
    for find, replace in COMPONENT:
        if component.count(find) != 1:
            report(False, 'a split by part of the system stays valid', f"the fixture no longer holds once: {find!r}")
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

    start, end = base.find('  deployer_roles:\n'), base.find('    source: { forced_by: [deployment.resource_groups_created')
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

    with open(IMPORTED, encoding='utf-8', newline='') as f:
        imported = f.read().replace('\r\n', '\n')
    rc, out = run(imported)
    report(rc == 0 and 'imports - 2 adopted resource(s)' in out and '2 unmapped item(s)' in out,
           'the import fixture passes, its unmapped items reported', out[-600:])
    rc, out = run(imported, [WRITE, '--check', '--no-stamp'])
    report(rc == 0, 'the import fixture is canonical', out[-400:])
    for name, find, replace, expected in IMPORT_MUTATIONS:
        if imported.count(find) != 1:
            report(False, name, f"the mutation text is in the import fixture {imported.count(find)} times: {find[:60]!r}")
            continue
        rc, out = run(imported.replace(find, replace))
        report(rc == 1 and expected in out, f"breaks: {name}", f"expected exit 1 with {expected!r}; got exit {rc}:\n{out[-500:]}")

    shape = shape_example()
    if shape is None:
        report(False, 'the Shape example of spec.md passes', "references/spec.md has no ```yaml block under '## Shape'")
        report(False, 'the Shape example of spec.md is canonical', 'see above')
    else:
        rc, out = run(shape)
        report(rc == 0 and 'Contract ok' in out, 'the Shape example of spec.md passes', out[-600:])
        rc, out = run(shape, [WRITE, '--check', '--no-stamp'])
        report(rc == 0, 'the Shape example of spec.md is canonical', out[-400:])
        for name, find, replace, expected, *appended in SHAPE_MUTATIONS:
            if shape.count(find) != 1:
                report(False, name, f"the mutation text is in the Shape example {shape.count(find)} times: {find[:60]!r}")
                continue
            # a fifth field is appended to the example's open: list, its last section
            rc, out = run(shape.replace(find, replace) + ''.join(appended))
            ok = rc == 0 and 'Contract ok' in out if expected is None else rc == 1 and expected in out
            report(ok, name if expected is None else f"breaks: {name}", f"expected {expected!r}; got exit {rc}:\n{out[-500:]}")
        for name, edits, expected in SHAPE_EDITS:
            text = shape
            for find, replace in edits:
                if text.count(find) != 1:
                    report(False, name, f"the edit text is in the Shape example {text.count(find)} times: {find[:60]!r}")
                    break
                text = text.replace(find, replace)
            else:
                rc, out = run(text)
                ok = rc == 0 and 'Contract ok' in out if expected is None else rc == 1 and expected in out
                report(ok, name if expected is None else f"breaks: {name}", f"expected {expected!r}; got exit {rc}:\n{out[-500:]}")

    print('-' * 70)
    total = 10 + len(MUTATIONS) + len(COMPONENT_MUTATIONS) + len(SHAPE_MUTATIONS) + len(IMPORT_MUTATIONS)
    print(f"{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
