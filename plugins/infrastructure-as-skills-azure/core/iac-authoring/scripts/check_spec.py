#!/usr/bin/env python3
"""Validates an infra-spec.yaml against the spec contract.

Read-only. Checks what the contract in references/spec.md promises:

  1. The file parses as YAML, and carries schema_version, spec.id and
     spec.target.
  2. Every decision value carries a known `source`. A value without one is a
     settings dump entry, not a recorded decision.
  3. `overridden` carries a reason, `forced` carries `forced_by`, and
     `requirement` carries `derived_from: deployment.<id>`. An undocumented
     exception reads as an accident a year later; a derived value without its
     requirement cannot be explained to the customer.
  4. `assumed` values and `open:` entries are reported, with what they block.
     A spec holding either is valid - it is not applyable, which is the
     distinction the exit code makes.
  5. No decision key uses a backend's attribute spelling
     (public_network_access_enabled, allowBlobPublicAccess, ...). The spec
     names decisions; one backend's vocabulary in it breaks the others.
  6. composition: unique module ids, every resource contained exactly once,
     `needs` pointing at declared modules and acyclic, `implementation`
     being avm|authored|reuse rather than a module path.
  7. Stages: context.environments is a non-empty list; a value that is a map
     keyed by stage names uses only those stages, and a stage it leaves out
     is named by an open entry (`environments:`) for that key.
  8. Resource groups: `resource_group_split` lists known roles only (never
     `main`) of the scheme `resource_group_scheme` names (concern by default,
     or lifecycle), and none under
     `resource_group_layout: single`; a split makes `resource_group_mode_<role>` required for `main`
     and every listed role, and a mode or a `context.resource_group_name_<role>`
     for a role that is not split off is stale; a resource's
     `placement.resource_group` names `main` or a split role;
     `resource_group_lock` is a known value.
  9. Context: `location` and `subscription_id`, and the name of every group
     whose mode is not `create`, are a value or an open entry - never asked,
     but never left to a value the run picks either. A warning, not an error:
     a stage file someone filled in carries them without the spec. A `create`
     group's name is computed by the render.
 10. Deployer roles: what the spec asks of the identity that deploys is in
     `deployment.deployer_roles` - `Contributor` on `subscription` for a
     `create` group, `Role Based Access Control Administrator` for any role
     assignment, `Key Vault Secrets Officer` on each vault with secret
     placeholders. A missing role is an error; a spec without the key is a
     warning (written before the key existed). Under `stage_isolation:
     resource_group` no group is `create` and no deployer role is scoped to
     `subscription`: either reaches every stage, and the separation is gone.

Needs PyYAML (pip install pyyaml). Without it the script says so and exits 2
rather than pretending the file is fine.

Usage:
    python3 check_spec.py ./infra-spec.yaml
    python3 check_spec.py ./infra-spec.yaml --require-applyable

Exit 0 clean, 1 contract violations, 2 could not check (no parser, no file).
"""

import argparse
import os
import re
import sys

KNOWN_SOURCES = ['stated', 'asked', 'platform', 'pattern', 'requirement', 'deployment', 'forced', 'assumed', 'default', 'carried', 'overridden']
KNOWN_BLOCKS = ['render', 'plan', 'apply']

# Attribute spellings that belong to a backend, not to a decision. Matched
# against decision keys only - a `renders:` field naming them is correct.
BACKEND_SPELLINGS = [
    'public_network_access_enabled', 'allow_nested_items_to_be_public',
    'shared_access_key_enabled_bool', 'https_traffic_only_enabled',
    'allowBlobPublicAccess', 'publicNetworkAccess', 'allowSharedKeyAccess',
    'supportsHttpsTrafficOnly', 'minimumTlsVersion', 'requireInfrastructureEncryption',
]

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'iac-rendering', 'scripts'))
import rg_roles  # noqa: E402 - the role table per scheme, shared with the diagram and the documents
RG_MODES = ['existing', 'create']
RG_LOCKS = ['production', 'all_stages', 'none']
# A role satisfies a need when it is the narrow one or broader; broader is the platform's call.
ROLES_ASSIGN = ['Role Based Access Control Administrator', 'User Access Administrator', 'Owner']
ROLES_SECRETS = ['Key Vault Secrets Officer', 'Key Vault Administrator', 'Owner']
ROLES_CREATE_GROUP = ['Contributor', 'Owner']


def load_question_index(yaml):
    """(resource or 'deployment', question id) -> question dict, from the plugin's sets."""
    index = {}

    def add(owner, doc):
        for g in (doc.get('groups') or []) if isinstance(doc, dict) else []:
            for q in (g.get('questions') or []):
                if isinstance(q, dict) and q.get('id'):
                    index[(owner, q['id'])] = q
    dep = os.path.join(HERE, '..', 'questions', 'deployment.yaml')
    if os.path.isfile(dep):
        with open(dep, encoding='utf-8') as f:
            add('deployment', yaml.safe_load(f))
    res_root = os.path.join(PLUGIN, 'resources')
    if os.path.isdir(res_root):
        for fam in os.listdir(res_root):
            fam_dir = os.path.join(res_root, fam)
            if os.path.isdir(fam_dir):
                for res in os.listdir(fam_dir):
                    qs = os.path.join(fam_dir, res, 'questions.yaml')
                    if os.path.isfile(qs):
                        with open(qs, encoding='utf-8') as f:
                            add(res, yaml.safe_load(f))
    return index


COLORS = {'cyan': '36', 'green': '32', 'red': '31', 'yellow': '33', 'gray': '90'}
USE_COLOR = sys.stdout.isatty() and not os.environ.get('NO_COLOR')


def say(text, color=None):
    if color and USE_COLOR:
        print(f"\033[{COLORS[color]}m{text}\033[0m")
    else:
        print(text)


def ok(text): say(f"[ ok ] {text}", 'green')
def bad(text): say(f"[fail] {text}", 'red')
def warn(text): say(f"[warn] {text}", 'yellow')


def main():
    ap = argparse.ArgumentParser(description='Validate an infra-spec.yaml against the spec contract.')
    ap.add_argument('path', help='the infra-spec.yaml to check')
    ap.add_argument('--require-applyable', action='store_true',
                    help='also fail on assumed values and on open entries that block apply')
    args = ap.parse_args()

    if not os.path.isfile(args.path):
        bad(f"no such file: {args.path}")
        return 2
    full = os.path.abspath(args.path)

    try:
        import yaml
    except ImportError:
        bad('no YAML parser available')
        say('       Install one and re-run:', 'gray')
        say('         pip install pyyaml', 'gray')
        return 2

    try:
        with open(full, encoding='utf-8') as f:
            spec = yaml.safe_load(f)
    except yaml.YAMLError as e:
        bad(f"YAML does not parse: {e}")
        return 1

    if spec is None:
        bad('the file parsed as empty')
        return 1

    say(f"Spec check - {full}", 'cyan')
    print('-' * 70)

    errors, warnings, notes = [], [], []

    def has(m, k): return isinstance(m, dict) and k in m
    def get(m, k): return m.get(k) if isinstance(m, dict) else None

    # --- 1. envelope -------------------------------------------------------
    for k in ('schema_version', 'spec'):
        if not has(spec, k):
            errors.append(f"top level: '{k}' is missing")
    head = get(spec, 'spec')
    for k in ('id', 'target'):
        if not has(head, k):
            errors.append(f"spec.{k} is missing")
    target = get(head, 'target')
    if target and target not in ('terraform', 'bicep'):
        errors.append(f"spec.target '{target}' is not terraform or bicep")
    pv = get(head, 'plugin_version')
    if pv is not None and not re.match(r'^\d+\.\d+\.\d+', str(pv)):
        warnings.append(f"spec.plugin_version '{pv}' is not a version (x.y.z); it is ignored and re-stamped on the next write")
    environments = get(get(spec, 'context'), 'environments')
    if not isinstance(environments, list) or not environments or not all(isinstance(e, str) for e in environments):
        errors.append("context.environments is missing or not a list of stage names - the stack the code is deployed through, [development, test, production] by default")
        environments = []
    if 'environment' in (get(spec, 'context') or {}):
        errors.append("context.environment is the old single-stage field; the stack is context.environments")
    lang = get(get(spec, 'context'), 'language')
    if lang is None:
        warnings.append("context.language is missing - the customer's language (en, de) that the picture and the decision document are written in; the scripts fall back to en")
    elif not (isinstance(lang, str) and len(lang) == 2 and lang.isalpha() and lang.islower()):
        errors.append(f"context.language '{lang}' is not a two-letter lowercase code (en, de)")
    if not errors:
        ok(f"envelope - id '{get(head, 'id')}', target '{target}', stages {environments}")

    # open entries naming stages, keyed by decision path
    open_stages = {}
    for o in (get(spec, 'open') or []):
        if isinstance(o, dict) and o.get('key'):
            for e in (o.get('environments') or []):
                open_stages.setdefault(str(o['key']), set()).add(e)
    stage_maps = 0
    try:
        questions = load_question_index(yaml)
    except (yaml.YAMLError, OSError):
        questions = {}

    # --- 2-5. walk every decision ------------------------------------------
    decisions = 0
    assumed = []

    def walk(node, path):
        nonlocal decisions, stage_maps
        # A decision is a map carrying a `value`. Anything else is a container.
        if not isinstance(node, dict):
            return
        if 'value' in node:
            decisions += 1
            src = node.get('source')
            v = node['value']
            if environments and isinstance(v, dict) and v and all(k in environments for k in v):
                stage_maps += 1
                missing = [e for e in environments if e not in v]
                for e in missing:
                    if e not in open_stages.get(path, set()):
                        errors.append(f"{path} has no value for stage '{e}' and no open entry naming it")
                np = node.get('non_production')
                if np is not None and np not in ('default', 'stated'):
                    errors.append(f"{path}.non_production '{np}' is not default or stated")
                parts = path.split('.')
                owner = 'deployment' if parts[0] == 'deployment' else (parts[1].split('__')[0] if parts[0] == 'resources' and len(parts) > 1 else None)  # <set>__<instance>: a second one of a kind
                q = questions.get((owner, parts[-1]))
                if q is not None and not q.get('per_environment') and 'non_production_default' not in q and src != 'overridden':
                    errors.append(f"{path} is split by stage, but its question is neither per_environment nor a cost knob - one value for every stage, or the user's departure recorded as overridden")
            elif environments and isinstance(v, dict) and any(k in environments for k in v):
                errors.append(f"{path} mixes stage names and other keys in its value")
            if not src:
                errors.append(f"{path} has a value but no source. Strip provenance and the spec is a settings dump.")
            elif src not in KNOWN_SOURCES:
                errors.append(f"{path} has source '{src}', which is not one of: {', '.join(KNOWN_SOURCES)}")
            elif src == 'overridden':
                if not any(k in node for k in ('reason', 'note', 'departs_from')):
                    errors.append(f"{path} is overridden with no reason. An undocumented exception reads as an accident later.")
            elif src == 'forced':
                if 'forced_by' not in node:
                    errors.append(f"{path} is forced with no forced_by. The chain is the point - what forced it?")
            elif src == 'requirement':
                if not str(node.get('derived_from', '')).startswith('deployment.'):
                    errors.append(f"{path} is a requirement-derived value with no derived_from: deployment.<id>. The customer's answer is the point - which one?")
            elif src == 'assumed':
                assumed.append(path)
            return
        for k in node:
            key = str(k)
            if key.startswith('_'):
                continue  # _target_overrides is quarantined on purpose
            if key in BACKEND_SPELLINGS:
                errors.append(f"{path}.{key} uses a backend's attribute spelling. The spec names decisions; renderers know attributes.")
            walk(node[k], f"{path}.{key}")

    for section in ('deployment', 'resources', 'wiring'):
        if has(spec, section):
            walk(spec[section], section)

    # context values that are per-stage maps follow the same rule
    for key, v in (get(spec, 'context') or {}).items():
        if key != 'environments' and environments and isinstance(v, dict) and v and all(k in environments for k in v):
            stage_maps += 1
            for e in environments:
                if e not in v and e not in open_stages.get(f"context.{key}", set()):
                    errors.append(f"context.{key} has no value for stage '{e}' and no open entry naming it")

    if decisions == 0:
        warnings.append('no decisions found - deployment:, resources: and wiring: are all empty or absent')
    else:
        ok(f"{decisions} decision(s), each with a known source" + (f", {stage_maps} per-stage map(s)" if stage_maps else ''))

    # --- 6. composition ----------------------------------------------------
    if has(spec, 'composition'):
        comp = spec['composition']
        gran = get(comp, 'granularity')
        if gran and gran not in ('single', 'per-concern', 'per-resource', 'per-family'):
            errors.append(f"composition.granularity '{gran}' is not single, per-concern, per-resource or per-family")

        modules = [m for m in (get(comp, 'modules') or []) if m]
        ids = [get(m, 'id') for m in modules]
        dupes = sorted({i for i in ids if ids.count(i) > 1}, key=str)
        if dupes:
            errors.append(f"composition: duplicate module id(s): {', '.join(str(d) for d in dupes)}")

        for m in modules:
            mid = get(m, 'id')
            impl = get(m, 'implementation')
            if impl and impl not in ('avm', 'authored', 'reuse'):
                errors.append(f"composition.{mid}.implementation '{impl}' is not avm, authored or reuse. A module path belongs in the renderer.")
            for n in (get(m, 'needs') or []):
                if n and n not in ids:
                    errors.append(f"composition.{mid} needs '{n}', which is not a declared module")

        # needs must be acyclic
        edges = {get(m, 'id'): [n for n in (get(m, 'needs') or []) if n] for m in modules}
        state = {}

        def visit(node, stack):
            if state.get(node) == 'done':
                return
            if state.get(node) == 'open':
                errors.append(f"composition: needs cycle - {' -> '.join(stack + [node])}. Two modules that need each other are one module.")
                return
            state[node] = 'open'
            for n in edges.get(node, []):
                visit(n, stack + [node])
            state[node] = 'done'

        for i in ids:
            if i:
                visit(i, [])

        # every resource in exactly one module - moot for `single`, which is "one root, no modules" by contract
        if gran != 'single' and has(spec, 'resources'):
            contained = [c for m in modules for c in (get(m, 'contains') or []) if c]
            for r in (spec['resources'] or {}):
                hits = contained.count(r)
                if hits == 0:
                    errors.append(f"composition: resource '{r}' is in no module")
                if hits > 1:
                    errors.append(f"composition: resource '{r}' is in {hits} modules; it belongs to exactly one")

        if modules:
            ok(f"composition - {len(modules)} module(s), needs acyclic")

    # --- 8. resource groups ------------------------------------------------
    rg_errors = len(errors)
    dep_node = get(spec, 'deployment') or {}
    scheme = rg_roles.scheme_of(dep_node)
    rg_table = rg_roles.load(yaml)
    split_roles = rg_roles.roles(rg_table, scheme, (get(spec, 'resources') or {}).keys())
    main_present = rg_roles.has_main(dep_node)
    ctx_node = get(spec, 'context') or {}

    def dep_value(qid):
        d = get(dep_node, qid)
        return d.get('value') if isinstance(d, dict) else None

    split = dep_value('resource_group_split')
    if split is None:
        split = []
    if not isinstance(split, list):
        errors.append("deployment.resource_group_split is not a list of roles")
        split = []
    for r in split:
        if r == 'main':
            errors.append("deployment.resource_group_split lists 'main' - the list holds the roles of the scheme; under a split there is no main group")
        elif r not in split_roles:
            errors.append(f"deployment.resource_group_split lists '{r}', which is not a role of the {scheme} scheme "
                          f"({', '.join(split_roles) or 'no resources yet'})")
    if len(set(map(str, split))) != len(split):
        errors.append("deployment.resource_group_split lists a role twice")
    layout = dep_value('resource_group_layout')
    if layout == 'single' and split:
        errors.append("deployment.resource_group_split lists roles, but resource_group_layout is single - one group per stage, nothing split off")
    if layout == 'single' and dep_value('resource_group_scheme') is not None:
        errors.append("deployment.resource_group_scheme is stale - resource_group_layout is single, so there is nothing to split")
    if layout == 'split' and not split:
        errors.append("deployment.resource_group_split is empty under resource_group_layout split - there is no main group, so the resources need the scheme's groups")
    if layout is None and split:
        warnings.append("deployment.resource_group_layout is missing - a spec written before it, read with a main group beside the split roles; a run re-derives the split without one")
    split = [r for r in split if r in split_roles]
    in_play = (['main'] if main_present else []) + split

    # every role named anywhere: the scheme's, and any a mode or a name was written for
    seen = set(split_roles) | {'main'}
    seen |= {k[len('resource_group_mode_'):] for k in dep_node if str(k).startswith('resource_group_mode_')}
    seen |= {k[len('resource_group_name_'):] for k in ctx_node if str(k).startswith('resource_group_name_')}
    seen.discard('kind')  # the question that stands for the per-kind keys, never a key itself
    for r in ['main'] + sorted(seen - {'main'}):
        mode = dep_value(f'resource_group_mode_{r}')
        mode_path = f'deployment.resource_group_mode_{r}'
        if mode is None:
            if split and r in in_play:
                errors.append(f"{mode_path} is missing - with a split every group says whether it exists or is created")
        else:
            if mode not in RG_MODES:
                errors.append(f"{mode_path} '{mode}' is not existing or create")
            if r not in in_play:
                errors.append(f"{mode_path} is stale - '{r}' has no group of its own"
                              + (" (under a split there is no main group)" if r == 'main' else ", it is not split off"))

        name_key = 'resource_group_name' if r == 'main' else f'resource_group_name_{r}'
        name = ctx_node.get(name_key) if isinstance(ctx_node, dict) else None
        if name is not None and r not in in_play:
            errors.append(f"context.{name_key} is stale - '{r}' has no group of its own"
                          + (" (under a split there is no main group)" if r == 'main' else ", it is not split off"))

    # under a split every resource needs a group of the scheme: there is no main to fall into
    if not main_present:
        for rkey, rnode in (get(spec, 'resources') or {}).items():
            if get(get(rnode, 'placement'), 'resource_group') is not None:
                continue  # a placement is checked below
            role = rg_roles.role_of(rg_table, scheme, str(rkey).split('__')[0])
            if role is not None and role not in split:
                errors.append(f"resources.{rkey} belongs to '{role}', which resource_group_split does not list - under a split "
                              f"there is no main group to fall back to; add the role, or place the resource with placement.resource_group")

    lock = dep_value('resource_group_lock')
    if lock is not None and lock not in RG_LOCKS:
        errors.append(f"deployment.resource_group_lock '{lock}' is not one of {', '.join(RG_LOCKS)}")
    rlock = dep_value('resource_lock')
    if rlock is not None and rlock not in RG_LOCKS:
        errors.append(f"deployment.resource_lock '{rlock}' is not one of {', '.join(RG_LOCKS)}")

    placed = 0
    for rkey, rnode in (get(spec, 'resources') or {}).items():
        d = get(get(rnode, 'placement'), 'resource_group')
        if d is None:
            continue
        placed += 1
        role = d.get('value') if isinstance(d, dict) else d
        if role not in in_play:
            errors.append(f"resources.{rkey}.placement.resource_group '{role}' names a group the deployment does not have - "
                          f"add the role to deployment.resource_group_split, or drop the placement (in play: {', '.join(in_play)})")
    if len(errors) == rg_errors and (split or placed):
        ok(f"resource groups - {'main and ' if main_present else 'no main group, '}{len(split)} split role(s), {placed} placement(s)")

    # --- 9. context: a value or an open entry ----------------------------------
    open_keys = {str(get(o, 'key')) for o in (get(spec, 'open') or []) if get(o, 'key')}
    required_ctx = ['location', 'subscription_id']
    for r in in_play:
        if dep_value(f'resource_group_mode_{r}') != 'create':
            required_ctx.append('resource_group_name' if r == 'main' else f'resource_group_name_{r}')
    for key in required_ctx:
        if ctx_node.get(key) in (None, '', {}) and f"context.{key}" not in open_keys:
            warnings.append(f"context.{key} has no value and no open entry - only right when every stage file already "
                            f"carries it; a run that was not told it writes an open entry and a placeholder")

    # --- 10. deployer roles ------------------------------------------------
    def filled(v):
        """A list value, or a stage map of lists, that holds at least one entry."""
        if isinstance(v, dict):
            return any(filled(x) for x in v.values())
        return bool(v)

    needs = []  # (what, accepted roles, accepted scopes, the decision that needs it)
    creates = [f'deployment.resource_group_mode_{r}' for r in in_play if dep_value(f'resource_group_mode_{r}') == 'create']
    if creates:
        needs.append(('a resource group is created', ROLES_CREATE_GROUP, ['subscription'], creates))
    assigning = []
    for rkey, rnode in (get(spec, 'resources') or {}).items():
        for gnode in (rnode or {}).values() if isinstance(rnode, dict) else []:
            d = get(gnode, 'role_assignments')
            if isinstance(d, dict) and filled(d.get('value')):
                assigning.append(f'resources.{rkey}')
        if str(rkey).split('__')[0] == 'key-vault':
            d = get(get(rnode, 'security'), 'secret_placeholders')
            if isinstance(d, dict) and filled(d.get('value')):
                needs.append((f"'{rkey}' holds secret placeholders", ROLES_SECRETS, [rkey, 'resource_group', 'subscription'],
                              [f'resources.{rkey}.security.secret_placeholders']))
    d = get(get(spec, 'wiring'), 'role_assignments')
    if isinstance(d, dict) and filled(d.get('value')):
        assigning.append('wiring.role_assignments')
    if assigning:
        needs.insert(0, ('roles are assigned', ROLES_ASSIGN, ['resource_group', 'subscription'], assigning))

    granted = dep_value('deployer_roles')
    dr_errors = len(errors)
    if dep_value('stage_isolation') == 'resource_group':
        for c in creates:
            errors.append(f"{c} is create under stage_isolation resource_group - creating a group needs a role on the "
                          f"shared subscription, which reaches every stage; the groups exist beforehand (existing)")
        for g in granted if isinstance(granted, list) else []:
            if isinstance(g, dict) and g.get('scope') == 'subscription':
                errors.append(f"deployment.deployer_roles grants {g.get('role')} on subscription under stage_isolation "
                              f"resource_group - each stage's identity holds roles on its own groups only")
    if granted is None:
        if needs:
            warnings.append("deployment.deployer_roles is missing - the spec needs "
                            + '; '.join(f"{n[1][0]} ({n[0]})" for n in needs)
                            + ". A run re-derives it; until then the hand-over cannot name them")
    elif not isinstance(granted, list) or not all(isinstance(g, dict) and g.get('role') and g.get('scope') for g in granted):
        errors.append("deployment.deployer_roles is not a list of { role, scope, for } entries")
    else:
        for what, roles, scopes, by in needs:
            if not any(g['role'] in roles and g['scope'] in scopes for g in granted):
                errors.append(f"deployment.deployer_roles has no {roles[0]} on {scopes[0]}, but {what} "
                              f"({', '.join(by[:3])}{' +' + str(len(by) - 3) if len(by) > 3 else ''}) - "
                              f"the first apply fails there")
        if len(errors) == dr_errors:
            ok(f"deployer roles - {len(granted)} grant(s) cover what the spec needs")

    # --- open: and assumed -------------------------------------------------
    blocking = []
    if has(spec, 'open'):
        for o in (spec['open'] or []):
            k = get(o, 'key')
            b = get(o, 'blocks')
            if not k:
                errors.append('open: an entry has no key')
            for e in (get(o, 'environments') or []):
                if environments and e not in environments:
                    errors.append(f"open.{k} names stage '{e}', which context.environments does not have")
            if not b:
                errors.append(f"open.{k} has no blocks: say what it stops - render, plan or apply")
            elif b not in KNOWN_BLOCKS:
                errors.append(f"open.{k} blocks '{b}', which is not render, plan or apply")
            else:
                notes.append(f"open: {k} (blocks {b})")
                blocking.append(f"{k} ({b})")
    for a in assumed:
        blocking.append(f"{a} (assumed)")

    print('-' * 70)
    for n in notes:
        say(f"  {n}", 'gray')
    if assumed:
        warn(f"{len(assumed)} assumed value(s) - renders and plans, never applies")
        for a in assumed:
            say(f"         {a}", 'gray')
    for w in warnings:
        warn(w)

    if errors:
        print()
        bad(f"{len(errors)} contract violation(s)")
        for e in errors:
            say(f"         {e}", 'gray')
        return 1

    if args.require_applyable and blocking:
        print()
        bad(f"not applyable - {len(blocking)} unresolved item(s)")
        for b in blocking:
            say(f"         {b}", 'gray')
        say('       Resolve them, or drop --require-applyable to check the contract only.', 'gray')
        return 1

    print()
    if blocking:
        say(f"Contract ok. {len(blocking)} item(s) still block apply - re-run with --require-applyable to fail on them.", 'yellow')
    else:
        say('Contract ok, nothing unresolved.', 'green')
    return 0


if __name__ == '__main__':
    sys.exit(main())
