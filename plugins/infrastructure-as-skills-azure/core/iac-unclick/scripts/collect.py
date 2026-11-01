#!/usr/bin/env python3
"""Reads what runs in Azure into inventory.json for map_inventory.py. Read only, the one Azure step.

    python collect.py --resource-group rg-orders-prod [--resource-group rg-2] [--subscription <id>]
                      [--tag workload=orders] [--no-diagnostics] [--out inventory.json]
    python collect.py --subscription <id> [--tag ...]

Every command it runs only reads: `az account show`, `az graph query` (resources,
resourcecontainers, authorizationresources), `az lock list`, and per resource
`az monitor diagnostic-settings list` (skipped with --no-diagnostics, the slow part on a large
scope). It never writes to Azure and needs no more than Reader on the scope. The rest of the
plugin never needs a login; this script is the only one that does.

The output format is map_inventory.py's docstring. Resource Graph rows are paged until the
skip token runs out, so a scope of any size is read whole.

Exit 0 written, 1 a query failed, 2 not run (no az, not logged in, no scope).
"""
import argparse
import datetime
import json
import shutil
import subprocess
import sys

PAGE = 1000


def az(args, az_path):
    """The parsed JSON of one read-only az call; raises RuntimeError with az's message."""
    p = subprocess.run([az_path, *args, '--only-show-errors', '-o', 'json'], capture_output=True, text=True,
                       encoding='utf-8')
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip()[-400:])
    return json.loads(p.stdout or 'null')


def graph(query, subscription, az_path):
    """Every row of a Resource Graph query, page after page."""
    rows, token = [], None
    while True:
        args = ['graph', 'query', '-q', query, '--subscriptions', subscription, '--first', str(PAGE)]
        if token:
            args += ['--skip-token', token]
        page = az(args, az_path) or {}
        rows += page.get('data') or []
        token = page.get('skip_token') or page.get('skipToken')
        if not token:
            return rows


def kql_list(values):
    return ', '.join("'" + v.replace("'", "\\'") + "'" for v in values)


def main():
    ap = argparse.ArgumentParser(description='Read a scope of Azure into inventory.json, read only.')
    ap.add_argument('--subscription', help='the subscription id (default: the current az account)')
    ap.add_argument('--resource-group', action='append', default=[], help='a group to read; repeat for several')
    ap.add_argument('--tag', action='append', default=[], help='name=value; only rows carrying it')
    ap.add_argument('--no-diagnostics', action='store_true', help='skip the diagnostic settings (one call per resource)')
    ap.add_argument('--out', default='inventory.json')
    args = ap.parse_args()

    az_path = shutil.which('az')
    if not az_path:
        print('[fail] the Azure CLI (az) is not on PATH - install it, then az login')
        return 2
    try:
        account = az(['account', 'show'], az_path)
    except RuntimeError as e:
        print(f"[fail] not logged in: {e}\n       az login, then run this again")
        return 2
    sub = args.subscription or account.get('id')
    groups = [g.lower() for g in args.resource_group]
    tags = dict(t.split('=', 1) for t in args.tag if '=' in t)
    scopes = ([f"/subscriptions/{sub}/resourceGroups/{g}" for g in args.resource_group] if groups
              else [f"/subscriptions/{sub}"])
    where = f"| where tolower(resourceGroup) in ({kql_list(groups)})" if groups else ''
    where += ''.join(f" | where tostring(tags['{k}']) =~ '{v}'" for k, v in tags.items())

    try:
        print(f"reading {', '.join(scopes)} ...")
        resources = graph(
            f"resources {where} | project id, name, type, kind, location, resourceGroup, subscriptionId, "
            f"managedBy, sku, plan, identity, zones, tags, properties, extendedLocation", sub, az_path)
        rg_where = f"| where tolower(name) in ({kql_list(groups)})" if groups else ''
        resource_groups = graph(
            "resourcecontainers | where type =~ 'microsoft.resources/subscriptions/resourcegroups' "
            f"{rg_where} | project id, name, managedBy, tags", sub, az_path)
        scope_filter = ' or '.join(f"tolower(tostring(properties.scope)) startswith '{s.lower()}'" for s in scopes)
        assignments = graph(
            "authorizationresources | where type =~ 'microsoft.authorization/roleassignments' "
            f"| where {scope_filter} | project id, properties", sub, az_path)
        definitions = graph(
            "authorizationresources | where type =~ 'microsoft.authorization/roledefinitions' "
            "| project id, roleName = tostring(properties.roleName)", sub, az_path)
        locks = []
        for g in (args.resource_group or [None]):
            found = az(['lock', 'list', '--subscription', sub] + (['--resource-group', g] if g else []), az_path) or []
            locks += [{'id': l['id'], 'properties': {'level': l.get('level')}} for l in found]
        diagnostics = []
        if not args.no_diagnostics:
            for i, r in enumerate(resources, 1):
                print(f"  diagnostic settings {i}/{len(resources)}", end='\r')
                try:
                    found = az(['monitor', 'diagnostic-settings', 'list', '--resource', r['id']], az_path)
                except RuntimeError:
                    continue  # a type without diagnostic settings answers with an error
                found = found.get('value', []) if isinstance(found, dict) else (found or [])
                diagnostics += [{'id': d['id'], 'properties': {k: v for k, v in d.items() if k not in ('id', 'name', 'type')}}
                                for d in found]
            print()
    except RuntimeError as e:
        print(f"[fail] {e}")
        return 1

    inventory = {
        'read_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'scopes': scopes,
        'tag_filter': tags,
        'resources': resources,
        'resource_groups': resource_groups,
        'role_assignments': assignments,
        # keyed by the definition's GUID: built-in ones read back as /providers/..., assignments
        # name them under the subscription
        'role_definitions': {str(d['id']).rsplit('/', 1)[-1].lower(): d.get('roleName') for d in definitions},
        'locks': locks,
        'diagnostic_settings': diagnostics,
    }
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=1)
    print(f"{args.out}: {len(resources)} resource(s), {len(assignments)} role assignment(s), {len(locks)} lock(s), "
          f"{len(diagnostics)} diagnostic setting(s)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
