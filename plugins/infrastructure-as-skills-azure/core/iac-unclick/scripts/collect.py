#!/usr/bin/env python3
"""Reads what runs in Azure into inventory.json for map_inventory.py. Read only, the one Azure step.

    python collect.py --resource-group rg-orders-prod [--resource-group rg-2] [--subscription <id>]
                      [--tag workload=orders] [--no-diagnostics] [--no-children] [--out inventory.json]
    python collect.py --subscription <id> [--tag ...]

Every command it runs only reads: `az account show` (also of the subscription, to stop on a
tenant other than the current account's, which Resource Graph cannot read), `az graph query` (resources,
resourcecontainers, authorizationresources), `az role definition list`, `az lock list`, and per resource
`az monitor diagnostic-settings list` (skipped with --no-diagnostics, the slow part on a large
scope) and one `az rest --method get` per child resource a set's render-map.yaml names under
`import_children` (blobServices/default, firewallRules, config/web; skipped with --no-children).
It never writes to Azure and needs no more than Reader on the scope. The rest of the
plugin never needs a login; this script is the only one that does.

The output format is map_inventory.py's docstring. Resource Graph rows are paged until the
skip token runs out, so a scope of any size is read whole.

Exit 0 written, 1 a query failed, 2 not run (no az, not logged in, no scope).
"""
import argparse
import datetime
import glob
import json
import os
import shutil
import subprocess
import sys

PAGE = 1000
PLUGIN = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))


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


def children_by_type():
    """ARM type (lower case) -> {child path: api version}, from every set's render-map.yaml."""
    import yaml  # the plugin's one dependency; only this step needs it here
    out = {}
    for qs in glob.glob(os.path.join(PLUGIN, 'resources', '*', '*', 'questions.yaml')):
        rm = os.path.join(os.path.dirname(qs), 'render-map.yaml')
        if not os.path.isfile(rm):
            continue
        with open(qs, encoding='utf-8') as f:
            rtype = str((yaml.safe_load(f) or {}).get('resource', '')).lower()
        with open(rm, encoding='utf-8') as f:
            children = (yaml.safe_load(f) or {}).get('import_children') or {}
        out.setdefault(rtype, {}).update({str(k): str(v) for k, v in children.items()})
    return out


def read_child(rid, child, version, az_path):
    """(read, body): the child's GET body; (True, None) when Azure has none (404), (False, None)
    when it could not be read - map_inventory treats the two differently."""
    try:
        return True, az(['rest', '--method', 'get', '--url', f"{rid}/{child}?api-version={version}"], az_path)
    except RuntimeError as e:
        text = str(e).lower()
        return ('notfound' in text or '(404)' in text or 'not found' in text), None


def kql_list(values):
    return ', '.join("'" + v.replace("'", "\\'") + "'" for v in values)


def main():
    ap = argparse.ArgumentParser(description='Read a scope of Azure into inventory.json, read only.')
    ap.add_argument('--subscription', help='the subscription id (default: the current az account)')
    ap.add_argument('--resource-group', action='append', default=[], help='a group to read; repeat for several')
    ap.add_argument('--tag', action='append', default=[], help='name=value; only rows carrying it')
    ap.add_argument('--no-diagnostics', action='store_true', help='skip the diagnostic settings (one call per resource)')
    ap.add_argument('--no-children', action='store_true', help='skip the child resources (one call per child)')
    ap.add_argument('--out', default='inventory.json')
    args = ap.parse_args()

    az_path = shutil.which('az')
    if not az_path:
        print('[fail] the Azure CLI (az) is not on PATH - install it, then az login')
        return 2
    try:  # az graph is an extension; without it az asks interactively and fails in a script
        az(['extension', 'show', '--name', 'resource-graph'], az_path)
    except RuntimeError:
        print('[fail] the az extension resource-graph is missing - az extension add --name resource-graph')
        return 2
    try:
        account = az(['account', 'show'], az_path)
    except RuntimeError as e:
        print(f"[fail] not logged in: {e}\n       az login, then run this again")
        return 2
    sub = args.subscription or account.get('id')
    # Resource Graph reads only the tenant of the current account: a subscription of another tenant
    # answers "NoValidSubscriptionsInQueryRequest", which names neither the tenant nor the fix.
    try:
        target = az(['account', 'show', '--subscription', sub], az_path)
    except RuntimeError as e:
        print(f"[fail] subscription {sub} is not among the logged-in accounts: {e}\n       az login, then run this again")
        return 2
    if str(target.get('tenantId', '')).lower() != str(account.get('tenantId', '')).lower():
        print(f"[fail] subscription {sub} ({target.get('name')}) is in tenant {target.get('tenantId')}, the current az "
              f"account ({account.get('name')}) in tenant {account.get('tenantId')} - Resource Graph reads only the "
              f"current one.\n       az account set --subscription {sub}, then run this again (and set it back after)")
        return 2
    groups =[g.lower() for g in args.resource_group]
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
        # Built-in roles are defined at the tenant, not in the subscription: Resource Graph filtered
        # by --subscriptions does not return them, `az role definition list` does (built-in and custom).
        definitions = az(['role', 'definition', 'list', '--subscription', sub,
                          '--query', '[].{id: name, roleName: roleName}'], az_path) or []
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
        children, unread = {}, 0
        if not args.no_children:
            wanted = children_by_type()
            jobs = [(r['id'], c, v) for r in resources for c, v in sorted(wanted.get(str(r.get('type', '')).lower(), {}).items())]
            for i, (rid, child, version) in enumerate(jobs, 1):
                print(f"  child resources {i}/{len(jobs)}", end='\r')
                ok, body = read_child(rid, child, version, az_path)
                if ok:
                    children.setdefault(rid.lower(), {})[child] = body
                else:
                    unread += 1
            if jobs:
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
        # an empty list read is "none configured"; skipped, it says nothing
        'diagnostics_read': not args.no_diagnostics,
        # {resource id (lower case): {child path: GET body, null when Azure has none}}; a child that
        # could not be read is absent, and its decisions are assumed
        'children': children,
    }
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=1)
    print(f"{args.out}: {len(resources)} resource(s), {len(assignments)} role assignment(s), {len(locks)} lock(s), "
          f"{len(diagnostics)} diagnostic setting(s), {sum(len(c) for c in children.values())} child resource(s)")
    if unread:
        print(f"[warn] {unread} child resource(s) could not be read - their decisions are assumed")
    return 0


if __name__ == '__main__':
    sys.exit(main())
