#!/usr/bin/env python3
"""Writes an infra-spec.yaml from an inventory of what runs in Azure. Offline: never reads Azure.

    python map_inventory.py <inventory.json> --stage production [--target terraform]
                            [--language de] [--workload orders] [--out infra-spec.yaml]

The inventory is what collect.py wrote (one scope read once), JSON:

  read_at            when Azure was read, UTC (2026-11-01T09:58:12Z)
  scopes             the subscription or resource group ids read
  tag_filter         {name: value} the rows were narrowed by, {} for none
  resources          Resource Graph rows of the `resources` table: id, name, type, kind,
                     location, resourceGroup, subscriptionId, managedBy, sku, identity,
                     zones, tags, properties
  resource_groups    rows of `resourcecontainers` for the groups in scope: id, name, managedBy
  role_assignments   rows of `authorizationresources`, type roleassignments: id, properties
                     {principalId, principalType, roleDefinitionId, scope}
  role_definitions   {role definition GUID (lower case): role name}
  locks              {id, properties: {level}} for every lock in scope
  diagnostic_settings  {id, properties: {workspaceId, ...}} - an id below the resource it is on

What it writes, and from where:

  - Each row is mapped to the question set whose `resource` is its type; where two sets share
    a type, `import_match` in their render-map.yaml decides by `kind`. A type without a set is
    `unmapped` (no_question_set). Nothing drops out silently.
  - A row of a type some set lists under `import_parts` belongs to the resource that names its
    id in its properties (a site's serverFarmId); a private endpoint belongs to the resource its
    privateLinkServiceConnections point at. It is adopted as that resource's part, not mapped.
  - Every decision is read through its render-map.yaml `import:` entry and nothing else:
    path + values | passthrough | format | reference | single | items | present, or cases.
    Read -> `source: imported`.
    Not read (todo, not_readable, absent from the row, not an answer) -> the question's default
    as `assumed`, and one open: entry per resource naming the decisions; a question without a
    default, or one that depends on another, is left out and named there too.
  - A reference is written as the resource (or subnet part) of the spec it points at, or as
    `{ existing: <kind>, id }` when it lies outside the scope.
  - adopt: the row's id, its CanNotDelete lock, its diagnostic setting to a workspace, its
    parts. A ReadOnly lock, a lock on a group and a second diagnostic setting are `unmapped`.
  - Role assignments on an adopted resource go to wiring.role_assignments with their adopt_id;
    the principal is the spec resource whose identity it is, else external:<type>-<objectId>
    (external:user-33bb1760-..., group, serviceprincipal) - a reader sees what kind of
    principal it is, the render keeps the object id. One
    on a scope the spec does not adopt (the group, the subscription) is `unmapped`.
  - deployment.network_exposure follows from what was read: `public` when any adopted
    resource's public_network_access is enabled or enabled_with_firewall, `private` when every
    one read is disabled; none read, none written.
  - Noise is left out and counted, never written: everything in NetworkWatcherRG and in a
    managed group (managedBy set), Smart Detector alert rules, and the tags Azure sets itself
    (hidden-*, ms-resource-usage, aks-managed-*).

The spec is then laid out by core/iac-authoring/scripts/write_spec.py and is a draft for the
review: check_spec.py validates it, export_decisions.py and iac-diagram show it.

Needs PyYAML. Exit 0 written, 1 written with nothing mapped, 2 not written.
"""
import argparse
import collections
import datetime
import glob
import json
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    print('PyYAML is required: pip install pyyaml')
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.abspath(os.path.join(HERE, '..', '..'))
PLUGIN = os.path.abspath(os.path.join(CORE, '..'))
WRITE_SPEC = os.path.join(CORE, 'iac-authoring', 'scripts', 'write_spec.py')
REF_KINDS = os.path.join(CORE, 'iac-authoring', 'references', 'ref-kinds.yaml')

NOISE_GROUPS = {'networkwatcherrg'}
NOISE_TYPES = {'microsoft.alertsmanagement/smartdetectoralertrules'}
NOISE_TAG = re.compile(r'^(hidden-|ms-resource-usage$|aks-managed-)', re.IGNORECASE)
PE_TYPE = 'microsoft.network/privateendpoints'
# Decisions every resource's set asks that the spec records once, in context.
CONTEXT_KEYS = {'placement.location', 'placement.resource_group_name', 'placement.environments'}
MISSING = object()


# --- the plugin's sets ---------------------------------------------------------------------

def fast_load(f):
    """safe_load through libyaml's C loader where PyYAML has it: every set and render-map is read."""
    return yaml.load(f, Loader=getattr(yaml, 'CSafeLoader', yaml.SafeLoader))


def load_sets():
    """name -> {type, questions [(group, q)], imports {group.q: import}, parts, match}."""
    sets = {}
    for qs in sorted(glob.glob(os.path.join(PLUGIN, 'resources', '*', '*', 'questions.yaml'))):
        name = os.path.basename(os.path.dirname(qs))
        with open(qs, encoding='utf-8') as f:
            doc = fast_load(f) or {}
        rm_path = os.path.join(os.path.dirname(qs), 'render-map.yaml')
        rm = {}
        if os.path.isfile(rm_path):
            with open(rm_path, encoding='utf-8') as f:
                rm = fast_load(f) or {}
        decisions = rm.get('decisions') or {}
        sets[name] = {
            'type': str(doc.get('resource', '')).lower(),
            'questions': [(g.get('id'), q) for g in doc.get('groups') or [] for q in g.get('questions') or []
                          if isinstance(q, dict) and q.get('id')],
            'imports': {k: v.get('import') for k, v in decisions.items() if isinstance(v, dict)},
            'rendered': {k for k, v in decisions.items() if isinstance(v, dict) and 'not_rendered' not in v},
            'parts': [str(t).lower() for t in rm.get('import_parts') or []],
            'match': rm.get('import_match') or {},
        }
    return sets


def kind_tokens(row):
    return {t.strip().lower() for t in str(row.get('kind') or '').split(',') if t.strip()}


def set_of(row, sets):
    """The set a row maps to: by type, then by import_match on kind where sets share the type."""
    t = str(row.get('type', '')).lower()
    cands = [n for n, s in sets.items() if s['type'] == t]
    if len(cands) <= 1:
        return cands[0] if cands else None
    tokens = kind_tokens(row)
    fits = []
    for n in cands:
        m = sets[n]['match']
        has = {str(x).lower() for x in m.get('kind_has') or []}
        lacks = {str(x).lower() for x in m.get('kind_lacks') or []}
        if m and (not has or has & tokens) and not (lacks & tokens):
            fits.append(n)
    return fits[0] if len(fits) == 1 else None


# --- reading one row -----------------------------------------------------------------------

def at(row, path):
    """The value at a dotted path of a row, MISSING when absent; keys match without case."""
    node = row
    for part in path.split('.'):
        if not isinstance(node, dict):
            return MISSING
        hit = next((k for k in node if k.lower() == part.lower()), None)
        if hit is None:
            return MISSING
        node = node[hit]
    return MISSING if node is None else node


def same(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b if isinstance(a, bool) and isinstance(b, bool) else str(a).lower() == str(b).lower()
    return str(a).lower() == str(b).lower()


def read(imp, row):
    """(found, value) - the raw answer an import entry reads from a row, before it is checked."""
    if not isinstance(imp, dict) or 'todo' in imp or 'not_readable' in imp:
        return False, None
    if 'cases' in imp:
        for c in imp['cases']:
            if all(at(row, p) is not MISSING and same(at(row, p), lit) for p, lit in c['when'].items()):
                return True, c['answer']
        return ('missing' in imp and all(at(row, p) is MISSING for c in imp['cases'] for p in c['when'])), imp.get('missing')
    v = at(row, imp['path'])
    if v is MISSING:
        return ('missing' in imp), imp.get('missing')
    if 'values' in imp:
        hit = next((a for lit, a in imp['values'].items() if same(lit, v)), MISSING)
        return (hit is not MISSING), (None if hit is MISSING else hit)
    if 'present' in imp:
        return True, (imp['present'] if v not in ('', [], {}) else imp.get('missing'))
    if 'single' in imp:
        return (isinstance(v, list) and len(v) == 1), (v[0] if isinstance(v, list) and len(v) == 1 else None)
    if 'items' in imp:
        if not isinstance(v, list):
            return False, None
        out = []
        for e in v:
            item = {f: at(e, p) for f, p in imp['items'].items()}
            if any(x is MISSING for x in item.values()):
                return False, None
            out.append(item)
        return True, out
    if 'format' in imp:
        pre, post = imp['format'].split('{value}')
        s = str(v)
        if s.lower().startswith(pre.lower()) and s.lower().endswith(post.lower()) and len(s) >= len(pre) + len(post):
            return True, s[len(pre):len(s) - len(post)]
        return False, None
    return True, v  # passthrough or reference


def fits(question, v):
    """The value spelled as the question accepts it, or MISSING when it is no answer."""
    t, acc = question.get('type'), question.get('accepts')
    if t == 'bool':
        if isinstance(v, bool):
            return v
        return {'true': True, 'false': False}.get(str(v).lower(), MISSING)
    if t == 'int':
        try:
            return int(v)
        except (TypeError, ValueError):
            return MISSING
    if isinstance(acc, list) and t in ('enum',):
        return next((a for a in acc if same(a, v)), MISSING)
    return v


def get_dec(node, group, qid):
    """An imported decision's value in a resource being written, None when it was not read."""
    d = (node.get(group) or {}).get(qid) if isinstance(node, dict) else None
    return d.get('value') if isinstance(d, dict) and d.get('source') == 'imported' else None


# --- the spec ------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description='Write an infra-spec.yaml from an inventory of what runs in Azure.')
    ap.add_argument('inventory')
    ap.add_argument('--stage', required=True, help='the stage the scope is (production, test, ...)')
    ap.add_argument('--target', default='terraform', choices=['terraform', 'bicep'])
    ap.add_argument('--language', default='en', choices=['en', 'de'])
    ap.add_argument('--workload', help='the workload short name (default: from the resource group name)')
    ap.add_argument('--out', default='infra-spec.yaml')
    args = ap.parse_args()

    try:
        with open(args.inventory, encoding='utf-8') as f:
            inv = json.load(f)
    except (OSError, ValueError) as e:
        print(f"[fail] cannot read {args.inventory}: {e}")
        return 2
    sets = load_sets()
    with open(REF_KINDS, encoding='utf-8') as f:
        ref_kinds = (yaml.safe_load(f) or {}).get('kinds') or {}
    stage = args.stage
    noise = collections.Counter()

    managed = {str(g.get('name', '')).lower() for g in inv.get('resource_groups') or [] if g.get('managedBy')}
    rows = []
    for r in inv.get('resources') or []:
        rg = str(r.get('resourceGroup', '')).lower()
        if rg in NOISE_GROUPS or rg in managed:
            noise['in NetworkWatcherRG or a managed group'] += 1
        elif str(r.get('type', '')).lower() in NOISE_TYPES:
            noise[str(r.get('type'))] += 1
        else:
            rows.append(r)
    by_id = {str(r['id']).lower(): r for r in rows}

    # --- parts: rows another resource renders ------------------------------------------
    part_types = {t for s in sets.values() for t in s['parts']}
    parent_of = {}
    blobs = {i: json.dumps(r.get('properties') or {}).lower() for i, r in by_id.items()}
    for rid, r in by_id.items():
        t = str(r.get('type', '')).lower()
        if t not in part_types:
            continue
        owners = []
        if t == PE_TYPE:
            conns = [c for p in ('properties.privateLinkServiceConnections', 'properties.manualPrivateLinkServiceConnections')
                     for c in (at(r, p) if isinstance(at(r, p), list) else [])]
            owners = [str(at(c, 'properties.privateLinkServiceId')).lower() for c in conns
                      if at(c, 'properties.privateLinkServiceId') is not MISSING]
        else:
            owners = [i for i, b in blobs.items() if i != rid and rid in b]
        owners = [o for o in owners if o in by_id and t in sets.get(set_of(by_id[o], sets) or '', {}).get('parts', [])]
        if len(set(owners)) == 1:
            parent_of[rid] = owners[0]

    # --- resources ---------------------------------------------------------------------
    unmapped, mapped = [], []
    for rid, r in sorted(by_id.items()):
        if rid in parent_of:
            continue
        s = set_of(r, sets)
        if s is None:
            unmapped.append({'type': r.get('type'), 'id': r['id'], 'reason': 'no_question_set'})
        else:
            mapped.append((s, r))
    count = collections.Counter(s for s, _ in mapped)
    key_of = {}
    for s, r in mapped:
        key = s if count[s] == 1 else f"{s}__{re.sub(r'[^a-z0-9-]', '-', str(r['name']).lower())}"
        key_of[str(r['id']).lower()] = key

    def principal_key(pid):
        for rid, r in by_id.items():
            if rid in key_of and (same(at(r, 'identity.principalId'), pid) or
                                  (str(r.get('type', '')).lower() == 'microsoft.managedidentity/userassignedidentities'
                                   and same(at(r, 'properties.principalId'), pid))):
                return key_of[rid]
        return None

    def reference(question, v, resources_out):
        rid = str(v).lower()
        kind = (question.get('accepts') or {}).get('ref')
        m = re.match(r'^(.*/providers/microsoft\.network/virtualnetworks/[^/]+)/subnets/([^/]+)$', rid)
        if m and m.group(1) in key_of:
            vnet = key_of[m.group(1)]
            names = json.dumps(resources_out.get(vnet, {}).get('addressing', {}).get('subnets', {})).lower()
            if f'"{m.group(2)}"' in names:
                return {'resource': vnet, 'part': str(v).split('/')[-1]}
        if rid in key_of:
            return {'resource': key_of[rid]}
        if kind and kind in ref_kinds:
            return {'existing': kind, 'id': {stage: v}}
        return MISSING

    resources_out, opens, read_n, assumed_n = {}, [], 0, 0
    order = sorted(mapped, key=lambda m: (str(m[1].get('type', '')) != 'Microsoft.Network/virtualNetworks', m[1]['id']))
    for s, r in order:  # networks first, so a subnet reference finds its part
        key = key_of[str(r['id']).lower()]
        node, missed = {}, []
        refs = []
        for gid, q in sets[s]['questions']:
            qkey = f"{gid}.{q['id']}"
            if qkey not in sets[s]['rendered'] or qkey in CONTEXT_KEYS:
                continue  # the group and the region are context's, written once below
            imp = sets[s]['imports'].get(qkey)
            if isinstance(imp, dict) and imp.get('reference'):
                refs.append((gid, q, imp))
                continue
            found, v = read(imp, r)
            v = fits(q, v) if found else MISSING
            if v is not MISSING:
                node.setdefault(gid, {})[q['id']] = {'value': v, 'source': 'imported'}
                read_n += 1
            elif 'default' in q and not q.get('depends_on'):
                node.setdefault(gid, {})[q['id']] = {'value': q['default'], 'source': 'assumed'}
                assumed_n += 1
                missed.append(qkey)
            else:
                missed.append(qkey)
        resources_out[key] = node
        for gid, q, imp in refs:
            found, v = read(imp, r)
            ref = reference(q, v, resources_out) if found else MISSING
            if ref is not MISSING:
                node.setdefault(gid, {})[q['id']] = {'value': ref, 'source': 'imported'}
                read_n += 1
            else:
                missed.append(f"{gid}.{q['id']}")
        if missed:
            opens.append({'key': f"resources.{key}",
                          'question': (f"Nicht aus Azure gelesen, mit der Vorgabe angenommen oder offen: {', '.join(missed)} - so übernehmen?"
                                       if args.language == 'de' else
                                       f"Not read from Azure, assumed from the default or left open: {', '.join(missed)} - keep them?"),
                          'blocks': 'apply'})

    # --- adopt: ids, locks, diagnostic settings, parts ------------------------------------
    locks = inv.get('locks') or []
    diags = inv.get('diagnostic_settings') or []
    any_lock = False
    for s, r in mapped:
        rid = str(r['id'])
        key = key_of[rid.lower()]
        adopt = {'id': {'value': {stage: rid}, 'source': 'imported'}}
        mine = [l for l in locks if str(l['id']).lower().startswith(rid.lower() + '/providers/microsoft.authorization/locks/')]
        for i, l in enumerate(mine):
            if i == 0 and str(at(l, 'properties.level')).lower() == 'cannotdelete':
                adopt['lock_id'] = {'value': {stage: l['id']}, 'source': 'imported'}
                any_lock = True
            else:
                unmapped.append({'type': 'Microsoft.Authorization/locks', 'id': l['id'], 'reason': 'outside_lock_policy'})
        mine = [d for d in diags if str(d['id']).lower().startswith(rid.lower() + '/providers/microsoft.insights/diagnosticsettings/')]
        for d in mine:
            if 'diagnostic_setting_id' not in adopt and at(d, 'properties.workspaceId') is not MISSING:
                adopt['diagnostic_setting_id'] = {'value': {stage: d['id']}, 'source': 'imported'}
            else:
                unmapped.append({'type': 'Microsoft.Insights/diagnosticSettings', 'id': d['id'],
                                 'reason': 'destination_not_supported'})
        parts = sorted(by_id[p]['id'] for p, owner in parent_of.items() if owner == rid.lower())
        if parts:
            adopt['parts'] = {'value': {stage: parts}, 'source': 'imported'}
        resources_out[key] = {'adopt': adopt, **resources_out[key]}
    adopted_ids = {str(r['id']).lower() for _, r in mapped}
    for l in locks:
        lid = str(l['id']).lower()
        if not any(lid.startswith(a + '/providers/') for a in adopted_ids):
            unmapped.append({'type': 'Microsoft.Authorization/locks', 'id': l['id'], 'reason': 'outside_lock_policy'})

    # --- role assignments ------------------------------------------------------------------
    names = {str(k).lower(): v for k, v in (inv.get('role_definitions') or {}).items()}
    assignments = []
    for a in inv.get('role_assignments') or []:
        scope = str(at(a, 'properties.scope')).lower()
        pid = at(a, 'properties.principalId')
        role = names.get(str(at(a, 'properties.roleDefinitionId')).rsplit('/', 1)[-1].lower())
        if scope not in key_of or not role:
            unmapped.append({'type': 'Microsoft.Authorization/roleAssignments', 'id': a['id'],
                             'reason': 'scope_not_adopted' if scope not in key_of else 'not_readable'})
            continue
        kind = str(at(a, 'properties.principalType') if at(a, 'properties.principalType') is not MISSING else 'principal').lower()
        assignments.append({'from': principal_key(pid) or f"external:{kind}-{pid}", 'to': key_of[scope],
                            'role': role, 'adopt_id': {stage: a['id']}})

    # --- context, deployment, head ---------------------------------------------------------
    groups = sorted({str(r.get('resourceGroup')) for _, r in mapped})
    subs = sorted({str(r.get('subscriptionId')) for _, r in mapped})
    locs = collections.Counter(str(r.get('location')) for _, r in mapped if r.get('location') not in (None, 'global'))
    tag_sets = [{k: v for k, v in (r.get('tags') or {}).items() if not NOISE_TAG.match(k)} for _, r in mapped]
    common = dict(set.intersection(*[set(t.items()) for t in tag_sets])) if tag_sets else {}
    workload = args.workload or re.sub(r'^rg-|-(prod|production|dev|test|tst|stg)$', '', (groups or ['workload'])[0].lower())
    context = {'environments': [stage], 'language': args.language}
    if locs:
        context['location'] = locs.most_common(1)[0][0]
    context['workload'] = re.sub(r'[^a-z0-9-]', '-', workload)
    if subs:
        context['subscription_id'] = {stage: subs[0]}
    if len(groups) == 1:
        context['resource_group_name'] = {stage: groups[0]}
    elif groups:
        opens.append({'key': 'context.resource_group_name',
                      'question': f"Several resource groups were read ({', '.join(groups)}); one layout and its groups are decided in the review.",
                      'blocks': 'render'})
    if common:
        context['tags'] = common
    for _, r in mapped:  # one region for all but the Foundry account, which a person departs with
        if locs and r.get('location') not in (None, 'global') and not same(r['location'], context['location']):
            opens.append({'key': f"resources.{key_of[str(r['id']).lower()]}",
                          'question': f"{r['name']} runs in {r['location']}, not in {context['location']} - move it, "
                                      f"or name why it departs (placement.location, Foundry only)",
                          'blocks': 'render'})
    scope_is_sub = all('/resourcegroups/' not in str(s).lower() for s in inv.get('scopes') or [])
    deployment = {
        'deployment_scope': {'value': 'subscription' if scope_is_sub else 'resource_group', 'source': 'imported'},
        'resource_groups_created': {'value': [], 'source': {'forced_by': 'deployment.deployment_scope'}},
        'resource_lock': {'value': ('production' if stage == 'production' else 'all_stages') if any_lock else 'none',
                          'source': 'imported'},
    }
    exposure = [str(get_dec(n, 'networking', 'public_network_access')) for n in resources_out.values()
                if get_dec(n, 'networking', 'public_network_access') is not None]
    if exposure:
        deployment['network_exposure'] = {
            'value': 'public' if any(e in ('enabled', 'enabled_with_firewall') for e in exposure) else 'private',
            'source': 'imported'}
    if assignments:
        deployment['deployer_roles'] = {
            'value': [{'role': 'Role Based Access Control Administrator', 'scope': 'resource_group',
                       'for': ['wiring.role_assignments']}],
            'source': {'forced_by': 'wiring.role_assignments'}}
    read_at = str(inv.get('read_at') or '')
    spec = {
        'schema_version': 1,
        'spec': {'id': context['workload'], 'target': args.target, 'generated_by': 'infrastructure-as-skills-azure',
                 'at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                 'imported_from': {'scopes': inv.get('scopes') or [], 'tag_filter': inv.get('tag_filter') or {},
                                   'read_at': read_at}},
        'context': context,
        'deployment': deployment,
        'resources': resources_out,
    }
    if assignments:
        spec['wiring'] = {'role_assignments': {'value': assignments, 'source': 'imported'}}
    if unmapped:
        spec['unmapped'] = unmapped
    opens.append({'key': 'deployment.deploy_mechanism',
                  'question': ('Über welches System wird ausgerollt (GitHub, Azure DevOps, GitLab, lokal)?' if args.language == 'de'
                               else 'Which system deploys it (GitHub, Azure DevOps, GitLab, local)?'),
                  'owner': 'Workload-Owner' if args.language == 'de' else 'workload owner', 'blocks': 'apply'})
    spec['open'] = opens

    with open(args.out, 'w', encoding='utf-8', newline='\n') as f:
        yaml.safe_dump(spec, f, sort_keys=False, allow_unicode=True, width=120)
    lay = subprocess.run([sys.executable, WRITE_SPEC, args.out], capture_output=True, text=True)
    print(f"{args.out}: {len(mapped)} resource(s) mapped, {len(parent_of)} part(s) adopted with them, "
          f"{len(unmapped)} unmapped, {sum(noise.values())} noise left out")
    print(f"  decisions: {read_n} imported, {assumed_n} assumed from defaults; {len(assignments)} role assignment(s)")
    for what, n in noise.most_common():
        print(f"  noise: {n} x {what}")
    if lay.returncode != 0:
        print(f"[warn] write_spec.py did not lay it out: {(lay.stdout + lay.stderr).strip()[-300:]}")
    return 0 if mapped else 1


if __name__ == '__main__':
    sys.exit(main())
