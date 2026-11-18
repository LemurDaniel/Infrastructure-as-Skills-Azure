#!/usr/bin/env python3
"""Validates an infra-spec.yaml against the spec contract.

Read-only. Checks what the contract in references/spec.md promises:

  1. The file parses as YAML, and carries schema_version, spec.id and
     spec.target. schema_version is the spec format's (SPEC_SCHEMA_VERSION); a newer
     one fails - this plugin does not know the format.
  2. Every decision value carries a known `source`: a word (spec_source.WORDS) or
     a map of one key. A value without one is a settings dump entry, not a
     recorded decision.
  3. `{overridden: <reason>}` carries a reason, `{forced_by: ...}` a pointer - and
     where that names a key (`deployment.<id>`, `resources.<key>.<group>.<id>`,
     `context.<id>`, `wiring.<part>`), the key exists in this spec or names a
     question of the sets - and `{derived_from: deployment.<id>}` the customer's
     answer. A pointer beside the source (`forced_by:`, `reason:`) fails. An undocumented
     exception reads as an accident a year later; a derived value without its
     requirement cannot be explained to the customer.
  4. `assumed` values and `open:` entries are reported, with what they block.
     A spec holding either is valid - it is not applyable, which is the
     distinction the exit code makes.
  4a. A resource decision is resources.<resource>.<group>.<question>, naming a
     question of the resource's set in that group (placement.resource_group and
     placement.location are every resource's). A role on a resource is no question of
     its set (`role_assignments`, `data_plane_role_assignments`): it is an entry of
     `wiring.role_assignments` with the resource as `to`.
  4b. An `enum` value, or each item of a `list` whose `accepts` is a list, is one
     its question accepts - per stage where the value is split by stage.
  5. No decision key uses a backend's attribute spelling
     (public_network_access_enabled, allowBlobPublicAccess, ...). The spec
     names decisions; one backend's vocabulary in it breaks the others.
  6. composition: unique module ids, every resource contained exactly once,
     `needs` pointing at declared modules and acyclic, `implementation`
     being avm|authored|reuse rather than a module path.
  6a. _target_overrides (top level or a resource's): keyed by terraform or bicep, each
     override { value, reason } with a reason - data, since a comment does not
     survive the parser the render reads the spec through.
  7. Stages: context.environments is a non-empty list; a value that is a map
     keyed by stage names uses only those stages, and a stage it leaves out
     is named by an open entry (`environments:`) for that key. A per_environment
     question with more than one stage is a map, unless it takes a reference.
  7a. References: a question with `accepts: { ref: <kind> }` holds {resource: <key>}
     (a resource of this spec of that kind, with `part:` where the kind is a part) or
     {existing: <kind>} with an id per stage of the kind's form, or an open entry for
     the id - never a bare name, a stage map or a name and resource group
     (spec_ref.py, references/ref-kinds.yaml).
  7b. A question marked `exclusive` (a subnet takes one NSG, one route table, one NAT
     gateway): no part is named by two resources of its set through it.
  7c. Every subnet a virtual-network of the spec creates - listed, or the implied private
     endpoint subnet - is named by a network-security-group, but those Azure refuses one on
     (NO_NSG_SUBNETS).
  8. Resource groups: the groups are derived (rg_roles.groups) - one, `main`, unless
     `resource_group_layout` is split; under a split every role of the scheme
     (`resource_group_scheme`: concern by default, lifecycle, protection, or component:
     `shared` and the parts the resources are placed in) that a resource is in, and no
     main group. `resource_group_split`, `resource_group_components` and every
     `resource_group_mode_<role>` are refused - `resource_groups_created` alone says which
     groups the render creates, and it names only groups that exist in the spec; a
     scheme without a split is stale; under a split every resource has a role (a kind
     the scheme does not place, and under component an unshared one, carries
     placement.resource_group), a placement names a role of the scheme; a
     `context.resource_group_name_<role>` for a group that does not exist is stale;
     `resource_group_lock` is a known value.
  9. Context: `location` and `subscription_id`, and the name of every group
     whose mode is not `create`, are a value or an open entry - never asked,
     but never left to a value the run picks either. A warning, not an error:
     a stage file someone filled in carries them without the spec. A `create`
     group's name is computed by the render. A resource's `placement.location`
     is the Foundry account's only: one region, named by a person with a
     reason, not `context.location`, never under `data_residency: country`.
  9g. Wiring: an access line runs between resources of the spec and actors (users,
     internet, external:<name>); a role assignment in `wiring.role_assignments` is
     { from, to, role }, one list for every stage: `to` a resource of the spec, `from` a
     resource of the spec (its identity holds the role) or a principal outside it as a
     reference { existing: entra_group | principal } with an id per stage or an open entry
     naming `wiring.role_assignments`, `role` a role of built-in-roles.yaml (a role
     Microsoft renamed is a warning naming the current name); a
     `wiring.secrets` line is { app, setting, vault, secret_name } naming an application and a
     key vault of the spec and a secret the vault's `secret_placeholders` creates.
  9i. A keyless resource someone reaches has a role for them: a resource whose `local_auth`
     is `disabled` and that another resource reaches (`wiring.access`) while no
     `wiring.role_assignments` entry from that resource's identity (itself, or a
     user-assigned identity it names) is on it or on a resource inside it, and no open
     entry names `wiring.role_assignments`. A warning: the first call would be refused.
  9h. Pattern: `pattern.id` names a pattern the plugin ships and `pattern.answers` its
     asks, each a value the ask accepts. A value recorded `source: pattern` is exactly
     what that pattern answers for those answers - a resource decision, or a wiring list
     as a whole; anything else was decided by someone and says so (`stated`,
     `{ overridden: <reason> }`). `source: pattern` without a pattern fails.
 10. Deployer roles: what the spec asks of the identity that deploys is in
     `deployment.deployer_roles` - `Contributor` on `subscription` for a
     `create` group, `Role Based Access Control Administrator` for any entry of
     `wiring.role_assignments`, `Key Vault Secrets Officer` on each vault with secret
     placeholders, `Contributor` on `subscription` too for deployment_scope
     subscription. A `create` group under deployment_scope resource_group is an
     error. A `wiring.access` line is { from, to, label? } and nothing else. A missing role is an error; a spec without the key is a
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

KNOWN_BLOCKS = ['render', 'plan', 'apply']

# The version of the spec format this plugin reads and writes - not the question sets'
# schema_version, which versions their own format.
SPEC_SCHEMA_VERSION = 1
# Subnets Azure refuses an NSG on (guardrails.md, Network exposure); every other one the spec
# creates has one.
NO_NSG_SUBNETS = {'GatewaySubnet', 'AzureFirewallSubnet', 'AzureFirewallManagementSubnet', 'RouteServerSubnet'}
TARGETS = ('terraform', 'bicep')

# Attribute spellings that belong to a backend, not to a decision. Matched
# against decision keys only - a render-map.yaml naming them is correct.
BACKEND_SPELLINGS = [
    'public_network_access_enabled', 'allow_nested_items_to_be_public',
    'shared_access_key_enabled_bool', 'https_traffic_only_enabled',
    'allowBlobPublicAccess', 'publicNetworkAccess', 'allowSharedKeyAccess',
    'supportsHttpsTrafficOnly', 'minimumTlsVersion', 'requireInfrastructureEncryption',
    'shared_access_key_enabled', 'local_authentication_disabled', 'minimum_tls_version',
]

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'iac-rendering', 'scripts'))
import rg_roles  # noqa: E402 - the role table per scheme, shared with the diagram and the documents
sys.path.insert(0, HERE)
import spec_source  # noqa: E402 - a source as a word or {forced_by | derived_from | overridden: ...}
import spec_ref  # noqa: E402 - a reference as {resource: <key>} or {existing: <kind>}
import pattern_lib  # noqa: E402 - a pattern resolved for its answers
# Resource keys every resource may carry without its set asking them (spec.md: placement, meta).
BUILTIN_RESOURCE_KEYS = {('placement', 'resource_group'), ('placement', 'location'), ('meta', 'purpose')}
RG_LOCKS = ['production', 'all_stages', 'none']
# A role on a resource is a relationship between two parts, so it is wiring and no question of
# a resource set: these ids are refused as a resource decision.
ROLE_QUESTION_IDS = ('role_assignments', 'data_plane_role_assignments')
# What a principal outside the spec may be (ref-kinds.yaml): a group of people, or a workload
# identity - both an Entra object id per stage.
PRINCIPAL_KINDS = ('entra_group', 'principal')
# A role satisfies a need when it is the narrow one or broader; broader is the platform's call.
ROLES_ASSIGN = ['Role Based Access Control Administrator', 'User Access Administrator', 'Owner']
ROLES_SECRETS = ['Key Vault Secrets Officer', 'Key Vault Administrator', 'Owner']
ROLES_CREATE_GROUP = ['Contributor', 'Owner']


def load_question_index(yaml):
    """(resource or 'deployment', question id) -> question dict, from the plugin's sets."""
    return plugin_lib.question_index(yaml)


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'lib'))
import plugin_lib  # noqa: E402 - the printer, the paths and the set lookup every script shares
say, ok, bad, warn = plugin_lib.say, plugin_lib.ok, plugin_lib.bad, plugin_lib.warn


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
    sv = get(spec, 'schema_version')
    if has(spec, 'schema_version') and (not isinstance(sv, int) or isinstance(sv, bool) or sv < 1):
        errors.append(f"schema_version '{sv}' is not a spec format version (an integer, {SPEC_SCHEMA_VERSION} today)")
    elif isinstance(sv, int) and sv > SPEC_SCHEMA_VERSION:
        errors.append(f"schema_version {sv} is a spec format newer than this plugin reads ({SPEC_SCHEMA_VERSION}) - update the plugin")
    head = get(spec, 'spec')
    for k in ('id', 'target'):
        if not has(head, k):
            errors.append(f"spec.{k} is missing")
    target = get(head, 'target')
    if target and target not in TARGETS:
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
    open_stages, open_keys = {}, set()
    for o in (get(spec, 'open') or []):
        if isinstance(o, dict) and o.get('key'):
            if not o.get('environments'):
                open_keys.add(str(o['key']))
            for e in (o.get('environments') or []):
                open_stages.setdefault(str(o['key']), set()).add(e)
    open_whole = set(open_keys)   # the keys an entry names for every stage
    stage_maps = 0
    try:
        questions = load_question_index(yaml)
    except (yaml.YAMLError, OSError):
        questions = {}
    try:
        ref_kinds = spec_ref.load_kinds(yaml)
    except (yaml.YAMLError, OSError):
        ref_kinds = {}

    # --- 2-5. walk every decision ------------------------------------------
    decisions = 0
    assumed = []

    def names_question(key):
        # deployment.<id> or resources.<key>.<group>.<id> naming a question of the sets,
        # recorded in this spec or not (a default the spec leaves out still forces).
        parts = key.split('.')
        if parts[0] == 'deployment' and len(parts) == 2:
            return ('deployment', parts[1]) in questions
        if parts[0] == 'resources' and len(parts) == 4:
            return (parts[1].split('__')[0], parts[3]) in questions
        return False

    def resolves(key):
        # A dotted spec key, walked from the root: resources.app-service__web.identity.managed_identity.
        # A deployment-set question of the context group is recorded under context:, so
        # deployment.environments names context.environments.
        if names_question(key):
            return True
        if key.startswith('deployment.') and resolves('context.' + key[len('deployment.'):]):
            return True
        node = spec
        for part in key.split('.'):
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
        return True

    owners = {o for o, _ in questions}

    def check_known(path):
        # A resource decision is resources.<key>.<group>.<id> naming a question of the
        # resource's set in that group. An invented key renders as raw JSON in the decision
        # document and reaches no renderer. A resource without a set is said out loud elsewhere.
        parts = path.split('.')
        if parts[0] != 'resources' or len(parts) < 2 or parts[1].split('__')[0] not in owners:
            return
        res = parts[1].split('__')[0]
        if len(parts) != 4:
            errors.append(f"{path} is not resources.<resource>.<group>.<question> - a decision sits under a group, one level deep")
            return
        if tuple(parts[2:]) in BUILTIN_RESOURCE_KEYS:
            return
        q = questions.get((res, parts[3]))
        if q is None and parts[3] in ROLE_QUESTION_IDS:
            errors.append(f"{path} names no question of the {res} set - a role on a resource is wiring: "
                          f"an entry {{ from: <identity>, to: {parts[1]}, role: <role> }} in wiring.role_assignments")
        elif q is None:
            errors.append(f"{path} names no question of the {res} set - an invented key reaches no renderer")
        elif q.get('_group') != parts[2]:
            errors.append(f"{path} is in group '{parts[2]}', but the {res} set asks {parts[3]} in '{q.get('_group')}'")

    def check_accepts(path, v):
        # An enum's value, or each item of a list with a list `accepts`, is one the set
        # offers - per stage where the value is split by stage.
        parts = path.split('.')
        if parts[0] == 'deployment' and len(parts) == 2:
            q = questions.get(('deployment', parts[1]))
        elif parts[0] == 'resources' and len(parts) == 4:
            q = questions.get((parts[1].split('__')[0], parts[3]))
            if q is not None and q.get('_group') != parts[2]:
                q = None
        else:
            return
        acc = (q or {}).get('accepts')
        if not isinstance(acc, list) or q.get('type') not in ('enum', 'list'):
            return
        allowed = {str(a).lower() for a in acc}
        staged = v.items() if environments and isinstance(v, dict) and v and all(k in environments for k in v) else [(None, v)]
        for stage, sv in staged:
            items = sv if q['type'] == 'list' and isinstance(sv, list) else [sv]
            for item in items:
                if item is None or isinstance(item, (dict, list)):
                    continue
                if str(item).lower() not in allowed:
                    where = f" (stage {stage})" if stage else ''
                    errors.append(f"{path}{where} is '{item}', which is not one of its question's accepts: {', '.join(str(a) for a in acc)}")

    def question_of(path):
        # The question a decision path answers: deployment.<id> or resources.<key>.<group>.<id>.
        parts = path.split('.')
        owner = 'deployment' if parts[0] == 'deployment' else (parts[1].split('__')[0] if parts[0] == 'resources' and len(parts) > 1 else None)  # <set>__<instance>: a second one of a kind
        return questions.get((owner, parts[-1]))

    def walk(node, path):
        nonlocal decisions, stage_maps
        # A decision is a map carrying a `value`. Anything else is a container.
        if not isinstance(node, dict):
            return
        if 'value' in node:
            decisions += 1
            src, ref = spec_source.kind(node.get('source'))
            v = node['value']
            kind = spec_ref.kind_of(question_of(path))
            if kind:
                # A reference is one value; its per-stage part is the existing id inside it.
                errors.extend(spec_ref.check(path, v, kind, ref_kinds, get(spec, 'resources') or {},
                                             environments, open_stages, open_keys))
                if (question_of(path) or {}).get('exclusive'):
                    owner = path.split('.')[1].split('__')[0]
                    for r in spec_ref.items(v):
                        if isinstance(r, dict) and r.get('resource') and r.get('part'):
                            claims.setdefault((owner, path.split('.')[-1], r['resource'], r['part']), []).append(path)
            elif environments and isinstance(v, dict) and v and all(k in environments for k in v):
                stage_maps += 1
                missing = [e for e in environments if e not in v]
                for e in missing:
                    if e not in open_stages.get(path, set()):
                        errors.append(f"{path} has no value for stage '{e}' and no open entry naming it")
                q = question_of(path)
                if q is not None and not q.get('per_environment') and 'non_production_default' not in q and not q.get('stage_parameter') and src != 'overridden':
                    errors.append(f"{path} is split by stage, but its question is neither per_environment nor a cost knob - one value for every stage, or the user's departure recorded as overridden")
            elif environments and isinstance(v, dict) and any(k in environments for k in v):
                errors.append(f"{path} mixes stage names and other keys in its value")
            elif len(environments) > 1 and v not in (None, '', [], {}):
                # per_environment: what lies outside the spec (a range, a name, a prefix) is a
                # parameter from the stage file, a map even where the stages agree - one value
                # would render as a literal. A reference is the exception, handled above.
                q = question_of(path)
                if q is not None and q.get('per_environment'):
                    errors.append(f"{path} is one value, but its question is per_environment and the value lies outside "
                                  f"this spec - a map keyed by stage ({', '.join(environments)}), a stage nobody could "
                                  f"answer for named in an open entry")
            check_known(path)
            check_accepts(path, v)
            if 'non_production' in node:
                errors.append(f"{path} carries non_production - a cost saving is derived from the question's "
                              f"non_production_default and deployment.non_production_savings, never recorded")
            stray = [k for k in ('forced_by', 'derived_from', 'reason', 'note', 'departs_from') if k in node]
            if stray:
                errors.append(f"{path} carries {', '.join(stray)} beside its source - the pointer is the source: "
                              f"source: {{forced_by | derived_from | overridden: ...}}")
            raw = node.get('source')
            if raw in (None, '', {}):
                errors.append(f"{path} has a value but no source. Strip provenance and the spec is a settings dump.")
            elif src is None:
                key = next((k for k, v in spec_source.POINTERS.items() if v == raw), None)
                errors.append(f"{path} has source {raw!r}, which is not one of {', '.join(spec_source.WORDS)} "
                              f"or a map of one key ({', '.join(spec_source.POINTERS)})"
                              + (f" - write source: {{{key}: ...}}" if key else ''))
            elif src == 'overridden':
                if not str(ref or '').strip():
                    errors.append(f"{path} is overridden with no reason. An undocumented exception reads as an accident later.")
            elif src == 'forced':
                for key in (ref if isinstance(ref, list) else [ref]):
                    if not str(key or '').strip():
                        errors.append(f"{path} is forced with no forced_by. The chain is the point - what forced it?")
                    elif re.match(r'^(deployment|context|resources|wiring)\.', str(key)) and not resolves(str(key)):
                        errors.append(f"{path} is forced_by '{key}', which is neither a key in this spec nor a question of the sets - a chain that points nowhere explains nothing")
            elif src == 'requirement':
                if not str(ref or '').startswith('deployment.'):
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

    claims = {}  # (set, question, resource, part) -> the decisions claiming it, for `exclusive`
    for section in ('deployment', 'pattern', 'resources', 'wiring'):
        if has(spec, section):
            walk(spec[section], section)
    for (owner, qid, res, part), by in claims.items():
        if len(by) > 1:
            errors.append(f"{part} of {res} is claimed by {len(by)} {owner} resources ({', '.join(by)}) - "
                          f"a part takes at most one, so all but one would be overwritten")
    # A subnet this spec creates without an NSG is open inside the network, and a landing zone's
    # policy refuses it at apply time.
    guarded = {(res, part) for (owner, _, res, part) in claims if owner == 'network-security-group'}
    subnet_kind = ref_kinds.get('subnet') or {}
    for rkey, rnode in (get(spec, 'resources') or {}).items():
        if str(rkey).split('__')[0] != 'virtual-network':
            continue
        for name in sorted(spec_ref.part_names(rnode, subnet_kind.get('part') or 'addressing.subnets', subnet_kind.get('implied'))):
            if name not in NO_NSG_SUBNETS and (str(rkey), name) not in guarded:
                errors.append(f"subnet {name} of {rkey} has no network security group - every subnet the spec "
                              f"creates gets one (a network-security-group whose networking.subnets names it)")

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

    # --- 6a. _target_overrides: per target, each override a value with its reason --------------
    # The reason is data, not a YAML comment: the render reads the spec through a parser (the
    # digest), and a comment does not survive one.
    overrides = [('_target_overrides', get(spec, '_target_overrides'))]
    overrides += [(f"resources.{r}._target_overrides", get(n, '_target_overrides'))
                   for r, n in (get(spec, 'resources') or {}).items()]
    for path, node in overrides:
        if node is None:
            continue
        if not isinstance(node, dict):
            errors.append(f"{path} is not a map keyed by target ({', '.join(TARGETS)})")
            continue
        for t, entries in node.items():
            if t not in TARGETS:
                errors.append(f"{path}.{t} is not a target - {', '.join(TARGETS)}")
                continue
            if not isinstance(entries, dict):
                errors.append(f"{path}.{t} is not a map of overrides")
                continue
            for name, o in entries.items():
                if not isinstance(o, dict) or 'value' not in o:
                    errors.append(f"{path}.{t}.{name} is not {{ value, reason }}")
                elif not str(o.get('reason') or '').strip():
                    errors.append(f"{path}.{t}.{name} has no reason - an override nobody explained reads as an accident")
                elif set(o) - {'value', 'reason'}:
                    errors.append(f"{path}.{t}.{name} holds {', '.join(sorted(set(o) - {'value', 'reason'}))} beside value and reason")

    # --- 8. resource groups ------------------------------------------------
    rg_errors = len(errors)
    dep_node = get(spec, 'deployment') or {}
    scheme = rg_roles.scheme_of(dep_node)
    rg_table = rg_roles.load(yaml)
    rg_resources = get(spec, 'resources') or {}
    split_roles = rg_roles.roles(rg_table, scheme, rg_resources)
    main_present = rg_roles.has_main(dep_node)
    ctx_node = get(spec, 'context') or {}

    def dep_value(qid):
        d = get(dep_node, qid)
        return d.get('value') if isinstance(d, dict) else None

    # Which groups exist is derived (rg_roles.groups): the layout, the scheme, and the role of
    # each resource - its placement, else its kind's. Nothing records the list.
    for key in ('resource_group_split', 'resource_group_components'):
        if get(dep_node, key) is not None:
            errors.append(f"deployment.{key} is no longer written - the groups follow from resource_group_layout, "
                          f"resource_group_scheme and each resource's role (placement.resource_group to move one)")
    layout = dep_value('resource_group_layout')
    if layout != 'split' and dep_value('resource_group_scheme') is not None:
        errors.append("deployment.resource_group_scheme is stale - resource_group_layout is not split, so there is nothing to split")
    split = rg_roles.groups(rg_table, dep_node, rg_resources)
    in_play = (['main'] if main_present else []) + split

    # Whether a group exists or is created is resource_groups_created alone: a group on it is
    # created, every other one exists. No mode per group is written.
    for k in dep_node:
        if str(k).startswith('resource_group_mode_'):
            errors.append(f"deployment.{k} is no longer written - resource_groups_created lists the groups the render "
                          f"creates, every other group exists")
    created_raw = dep_value('resource_groups_created')
    if created_raw is not None and not isinstance(created_raw, list):
        errors.append("deployment.resource_groups_created is not a list of groups")
    for r in rg_roles.created(dep_node):
        if r not in in_play:
            errors.append(f"deployment.resource_groups_created lists '{r}', which has no group"
                          + (" (under a split there is no main group)" if r == 'main' else ", no resource of the spec is in it"))

    # every role a name was written for: the scheme's, and any other
    seen = set(split_roles) | {'main'}
    seen |= {k[len('resource_group_name_'):] for k in ctx_node if str(k).startswith('resource_group_name_')}
    for r in ['main'] + sorted(seen - {'main'}):
        name_key = 'resource_group_name' if r == 'main' else f'resource_group_name_{r}'
        name = ctx_node.get(name_key) if isinstance(ctx_node, dict) else None
        if name is not None and r not in in_play:
            errors.append(f"context.{name_key} is stale - '{r}' has no group of its own"
                          + (" (under a split there is no main group)" if r == 'main' else ", no resource of the spec is in it"))

    # under a split every resource needs a group of the scheme: there is no main to fall into
    if not main_present:
        for rkey, rnode in (get(spec, 'resources') or {}).items():
            if get(get(rnode, 'placement'), 'resource_group') is not None:
                continue  # a placement is checked below
            kind = str(rkey).split('__')[0]
            role = rg_roles.role_of(rg_table, scheme, kind)
            if scheme == 'component' and role is None and kind not in (rg_table.get('attached') or []):
                errors.append(f"resources.{rkey} names no part - under the component scheme every resource that is not "
                              f"shared carries placement.resource_group with its part ({', '.join(split_roles[1:]) or 'none placed yet'})")
                continue
            if role == 'main':
                errors.append(f"resources.{rkey} has no role in the {scheme} scheme - under a split there is no main group "
                              f"to fall back to; place it with placement.resource_group ({', '.join(split_roles)})")

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
        if main_present and role != 'main':
            errors.append(f"resources.{rkey}.placement.resource_group '{role}' - resource_group_layout is not split, so the "
                          f"deployment has one group; drop the placement or split")
        elif not main_present and role not in split_roles:
            errors.append(f"resources.{rkey}.placement.resource_group '{role}' is not a role of the {scheme} scheme "
                          f"({', '.join(split_roles)})")
    if len(errors) == rg_errors and (split or placed):
        ok(f"resource groups - {'main and ' if main_present else 'no main group, '}{len(split)} split role(s), {placed} placement(s)")

    # --- 9. context: a value or an open entry ----------------------------------
    open_keys = {str(get(o, 'key')) for o in (get(spec, 'open') or []) if get(o, 'key')}
    required_ctx = ['location', 'subscription_id']
    for r in in_play:
        if rg_roles.mode(dep_node, r) != 'create':
            required_ctx.append('resource_group_name' if r == 'main' else f'resource_group_name_{r}')
    for key in required_ctx:
        if ctx_node.get(key) in (None, '', {}) and f"context.{key}" not in open_keys:
            warnings.append(f"context.{key} has no value and no open entry - only right when every stage file already "
                            f"carries it; a run that was not told it writes an open entry and a placeholder")

    # --- 9a. a region apart from context.location ------------------------------
    # Only the Foundry account departs, for a model its region's catalogue lacks: one region
    # for every stage, named by a person with its reason, never under country residency.
    region = ctx_node.get('location') if isinstance(ctx_node, dict) else None
    for rkey, rnode in (get(spec, 'resources') or {}).items():
        d = get(get(rnode, 'placement'), 'location')
        if d is None:
            continue
        where = f"resources.{rkey}.placement.location"
        if str(rkey).split('__')[0] != 'foundry':
            errors.append(f"{where} - only the Foundry account departs from context.location; everything else runs there")
            continue
        value = d.get('value') if isinstance(d, dict) else d
        if not isinstance(value, str) or not value:
            errors.append(f"{where} is not one region - the departure holds for every stage, not a map per stage")
            continue
        src, reason = spec_source.kind(d.get('source')) if isinstance(d, dict) else (None, None)
        if src != 'overridden':
            errors.append(f"{where} is {src} - a region apart from context.location is a departure a person names: "
                          f"source: {{overridden: <the model context.location does not offer>}}, or the model is an open entry")
        elif not str(reason or '').strip():
            errors.append(f"{where} carries no reason - name the model the region of context.location does not offer")
        if region and value == region:
            errors.append(f"{where} is context.location ({region}) - no departure, drop the key")
        if dep_value('data_residency') == 'country':
            errors.append(f"{where} '{value}' under data_residency country - the data stays in the country of "
                          f"context.location; the model is a named gap, or the customer revisits the residency")

    res_keys = set((get(spec, 'resources') or {}).keys())

    # A purpose belongs to its resource, not to the wiring between resources.
    if get(get(spec, 'wiring'), 'purposes') is not None:
        errors.append("wiring.purposes is no longer read - a resource's purpose is resources.<key>.meta.purpose")
    # A resource is in the spec and built, or it is not decided yet and an open entry.
    if get(get(spec, 'wiring'), 'optional') is not None:
        errors.append("wiring.optional is no longer read - a part nobody has decided on is an open: entry "
                      "(\"Soll der Redis-Cache gebaut werden?\", blocks: apply), a resource in the spec is built")

    # --- 9b. an access line is { from, to, label? } ------------------------------
    # An unquoted `label: Users, HTTPS` parses as a label plus a key `HTTPS: null`; the
    # diagram reads only from, to and label, so anything else is a parse accident.
    access = get(get(spec, 'wiring'), 'access')
    for i, a in enumerate((access.get('value') or []) if isinstance(access, dict) else []):
        if not isinstance(a, dict):
            errors.append(f"wiring.access[{i}] is not a mapping {{ from, to, label }}")
            continue
        extra = sorted(str(k) for k in a if k not in ('from', 'to', 'label'))
        if extra:
            errors.append(f"wiring.access[{i}] ({a.get('from')} -> {a.get('to')}) has unknown key(s) {', '.join(extra)} - "
                          f"a label with a comma must be quoted")
        for side in ('from', 'to'):
            if not isinstance(a.get(side), str) or not a.get(side):
                errors.append(f"wiring.access[{i}] has no '{side}'")
        if 'label' in a and not isinstance(a['label'], str):
            errors.append(f"wiring.access[{i}] label is not text")

    # --- 9g. wiring names what exists --------------------------------------------
    # The diagram skips an endpoint it does not know and the render has nothing to bind a
    # role or a secret reference to; a misspelt role passes every check until the first apply.
    wiring_node = get(spec, 'wiring') or {}

    def wiring_list(section):
        d = get(wiring_node, section)
        v = d.get('value') if isinstance(d, dict) else None
        return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []

    for a in wiring_list('access'):
        for side in ('from', 'to'):
            name = a.get(side)
            if isinstance(name, str) and name and name not in res_keys and not pattern_lib.is_actor(name):
                errors.append(f"wiring.access {a.get('from')} -> {a.get('to')}: '{name}' is neither a resource of this "
                              f"spec nor users, internet or external:<name> - the line is not drawn and nothing is wired")
    try:
        rbac_roles, data_plane_roles = pattern_lib.load_roles(yaml)
        renamed_roles = pattern_lib.load_renamed_roles(yaml)
    except (yaml.YAMLError, OSError):
        rbac_roles, data_plane_roles, renamed_roles = set(), set(), {}
    roles_value = get(get(wiring_node, 'role_assignments'), 'value')
    if environments and isinstance(roles_value, dict) and roles_value and all(k in environments for k in roles_value):
        errors.append("wiring.role_assignments is split by stage - a role is a relationship between two parts of the "
                      "system and holds in every stage: one list of { from, to, role }")
    for r in wiring_list('role_assignments'):
        src = r.get('from')
        outside = isinstance(src, dict)
        shown = (f"existing {src.get('existing')}" if 'existing' in src else str(src)) if outside else src
        where = f"wiring.role_assignments {shown} -> {r.get('to')}"
        extra = sorted(str(k) for k in r if k not in ('from', 'to', 'role'))
        if extra or not all(isinstance(r.get(k), str) and r.get(k) for k in ('to', 'role')) or not src \
                or not isinstance(src, (str, dict)):
            errors.append(f"{where} is not {{ from, to, role }}" + (f" (unknown: {', '.join(extra)})" if extra else ''))
            continue
        if r['to'] not in res_keys:
            errors.append(f"{where}: '{r['to']}' is not a resource of this spec - the role has no scope; a narrower "
                          f"scope is a narrower resource of the spec, a scope outside it a role-assignment resource")
        if not outside:
            if src not in res_keys:
                errors.append(f"{where}: '{src}' is not a resource of this spec - `from` is a resource key (its identity "
                              f"holds the role) or a principal outside the spec as {{ existing: {' | '.join(PRINCIPAL_KINDS)} }}")
        elif 'existing' not in src:
            errors.append(f"{where}: `from` is a resource key of this spec as plain text, or a principal outside it as "
                          f"{{ existing: {' | '.join(PRINCIPAL_KINDS)} }} - nothing else")
        elif src['existing'] not in PRINCIPAL_KINDS:
            errors.append(f"{where}: a principal outside the spec is {{ existing: {' | '.join(PRINCIPAL_KINDS)} }}, "
                          f"not existing: {src['existing']}")
        else:
            # checked like any other reference: an object id per stage, or an open entry naming the key
            errors.extend(spec_ref.check('wiring.role_assignments', src, src['existing'], ref_kinds,
                                         get(spec, 'resources') or {}, environments, open_stages, open_whole))
        if r['role'] in renamed_roles:
            # a warning: the definition id is the same, and a spec written before the rename is valid
            warnings.append(f"{where}: '{r['role']}' is called '{renamed_roles[r['role']]}' now (same role definition) - "
                            f"a render that looks the role up by name needs the current one")
        elif rbac_roles and r['role'] not in rbac_roles and r['role'] not in data_plane_roles:
            errors.append(f"{where}: '{r['role']}' is not a built-in role (built-in-roles.yaml) - a misspelt role "
                          f"fails at the first apply")
    for sref in wiring_list('secrets'):
        where = f"wiring.secrets {sref.get('app')}.{sref.get('setting')}"
        extra = sorted(str(k) for k in sref if k not in ('app', 'setting', 'vault', 'secret_name'))
        if extra or not all(isinstance(sref.get(k), str) and sref.get(k) for k in ('app', 'setting', 'vault', 'secret_name')):
            errors.append(f"{where} is not {{ app, setting, vault, secret_name }}" + (f" (unknown: {', '.join(extra)})" if extra else ''))
            continue
        if sref['app'] not in res_keys or pattern_lib.kind(sref['app']) not in pattern_lib.APP_KINDS:
            errors.append(f"{where}: '{sref['app']}' is not an application of this spec")
        if sref['vault'] not in res_keys or pattern_lib.kind(sref['vault']) != 'key-vault':
            errors.append(f"{where}: '{sref['vault']}' is not a key vault of this spec")
            continue
        held = get(get(get(get(spec, 'resources'), sref['vault']), 'security'), 'secret_placeholders')
        held = held.get('value') if isinstance(held, dict) else None
        names = {n for lst in (held.values() if isinstance(held, dict) else [held]) if isinstance(lst, list) for n in lst}
        if sref['secret_name'] not in names:
            errors.append(f"{where}: secret '{sref['secret_name']}' is not in resources.{sref['vault']}.security.secret_placeholders - "
                          f"the reference resolves to nothing at the first start")

    # --- 9i. a keyless resource that is reached has a role for the caller --------
    # With local authentication off, a caller gets in by a role or not at all. The role is on
    # the resource or on one inside it (a container of the account, a secret of the vault: a
    # resource that references it), held by the caller itself or by a user-assigned identity
    # it names. A warning - the roles may be granted outside the spec.
    def decisions_of(rnode):
        for gnode in (rnode or {}).values() if isinstance(rnode, dict) else []:
            for qid, d in (gnode.items() if isinstance(gnode, dict) else []):
                if isinstance(d, dict) and 'value' in d:
                    yield qid, d['value']

    def referenced(rnode):
        found = set()

        def scan(v):
            if isinstance(v, dict):
                if isinstance(v.get('resource'), str):
                    found.add(v['resource'])
                for x in v.values():
                    scan(x)
            elif isinstance(v, list):
                for x in v:
                    scan(x)
        for _, v in decisions_of(rnode):
            scan(v)
        return found

    all_resources = get(spec, 'resources') or {}
    role_pairs = {(r.get('from'), r.get('to')) for r in wiring_list('role_assignments') if isinstance(r.get('from'), str)}
    roles_open = 'wiring.role_assignments' in open_keys or 'wiring.role_assignments' in open_stages
    warned = set()
    for a in wiring_list('access'):
        caller, target = a.get('from'), a.get('to')
        if caller not in res_keys or target not in res_keys or caller == target or (caller, target) in warned or roles_open:
            continue
        local_auth = dict(decisions_of(all_resources.get(target))).get('local_auth')
        if 'disabled' not in (local_auth.values() if isinstance(local_auth, dict) else [local_auth]):
            continue
        holders = {caller} | {k for k in referenced(all_resources.get(caller)) if pattern_lib.kind(k) == pattern_lib.IDENTITY_KIND}
        scopes = {target} | {k for k, n in all_resources.items() if k != caller and target in referenced(n)}
        if not any((h, s) in role_pairs for h in holders for s in scopes):
            warned.add((caller, target))
            warnings.append(f"resources.{target} is keyless (local_auth: disabled) and reached by {caller} (wiring.access), "
                            f"but {caller} holds no role on it - no wiring.role_assignments entry from "
                            f"{' or '.join(sorted(holders))} to {target}, so its first call is refused; name the role, "
                            f"or write an open: entry with the key wiring.role_assignments")

    # --- 9h. the pattern, and what is recorded as its answer ------------------------
    # `source: pattern` is a claim a script can check: the pattern is data, so the value it
    # gives for the recorded answers is known. A value that differs was decided by someone.
    pattern_node = get(spec, 'pattern')
    applied = None
    if pattern_node is not None:
        pid = get(get(pattern_node, 'id'), 'value')
        pattern_doc = pattern_lib.load(yaml, str(pid)) if isinstance(pid, str) and pid in pattern_lib.pattern_ids() else None
        if not isinstance(pattern_doc, dict):
            errors.append(f"pattern.id '{pid}' is not a pattern of this plugin ({', '.join(pattern_lib.pattern_ids()) or 'it ships none'})")
        else:
            asks = {a.get('id'): a for a in (pattern_doc.get('asks') or []) if isinstance(a, dict)}
            given = {}
            for aid, d in (get(pattern_node, 'answers') or {}).items():
                value = d.get('value') if isinstance(d, dict) else d
                ask = asks.get(aid)
                if ask is None:
                    errors.append(f"pattern.answers.{aid} is no ask of pattern {pid} ({', '.join(map(str, asks)) or 'it asks nothing'})")
                elif isinstance(ask.get('accepts'), list) and value not in ask['accepts']:
                    errors.append(f"pattern.answers.{aid} is '{value}', which the ask does not accept: {', '.join(map(str, ask['accepts']))}")
                elif ask.get('type') == 'bool' and not isinstance(value, bool):
                    errors.append(f"pattern.answers.{aid} is '{value}', but the ask is answered true or false")
                else:
                    given[aid] = value
            applied, _ = pattern_lib.apply(pattern_doc, questions, given, environments=environments)

    def pattern_sourced(node, path):
        if not isinstance(node, dict):
            return
        if 'value' in node:
            if spec_source.kind(node.get('source'))[0] == 'pattern':
                yield path, node['value']
            return
        for k, v in node.items():
            yield from pattern_sourced(v, path + [str(k)])

    def lines(section, value):
        keys = {'access': ('from', 'to'), 'role_assignments': ('from', 'to', 'role'),
                'secrets': ('app', 'setting', 'vault', 'secret_name')}.get(section, ())
        return sorted(tuple(str(x.get(k)) for k in keys) for x in (value or []) if isinstance(x, dict))

    for section in ('deployment', 'resources', 'wiring'):
        for p, value in pattern_sourced(get(spec, section), [section]):
            where = '.'.join(p)
            if pattern_node is None:
                errors.append(f"{where} has source pattern, but the spec names no pattern (pattern.id)")
                continue
            if applied is None or p[-2:] == ['meta', 'purpose']:
                continue   # an unknown pattern is reported above; a purpose is the customer's wording
            expected = applied
            for part in p:
                expected = expected.get(part) if isinstance(expected, dict) else None
            if not isinstance(expected, dict) or 'value' not in expected:
                errors.append(f"{where} has source pattern, but pattern {pid} does not answer it for the recorded "
                              f"answers - a value someone decided is stated or {{ overridden: <reason> }}")
            elif (lines(p[1], value) != lines(p[1], expected['value'])) if section == 'wiring' else (value != expected['value']):
                errors.append(f"{where} has source pattern, but differs from what pattern {pid} answers for the "
                              f"recorded answers - a departure is {{ overridden: <reason> }}, an addition stated")

    # --- 9c. application monitoring brings its component ------------------------
    # `application_monitoring: enabled` with an application means one application-insights
    # resource; a spec without the key predates it and is not held to it.
    apps = sorted(k for k in res_keys if k.split('__')[0] in ('app-service', 'function-app', 'container-apps'))
    if dep_value('application_monitoring') == 'enabled' and apps:
        if not any(k.split('__')[0] == 'application-insights' for k in res_keys):
            errors.append(f"deployment.application_monitoring is enabled and the spec has {', '.join(apps)}, "
                          f"but no application-insights resource - the applications have nowhere to send telemetry")

    # --- 9d. a resource carries its decisions ------------------------------------
    # `observability_ownership: create` makes the workspace this deployment's; its own set
    # (public access, local auth) is only decided when it is a resource of the spec. A resource
    # written as `{}` whose set decides something of its own was never resolved through its set:
    # a renderer and the diagram would read the posture where the set has a default of its own.
    # Deciding means a question that always applies (no depends_on) and is asked, inherits a
    # deployment decision, or defaults a networking or security setting. A bare identity, whose
    # set holds nothing of the kind, stays valid.
    if dep_value('observability_ownership') == 'create' and 'log-analytics-workspace' not in res_keys:
        errors.append("deployment.observability_ownership is create, but the spec has no log-analytics-workspace "
                      "resource - the workspace's own decisions (public access, local auth) were never made")
    for rkey, rnode in (get(spec, 'resources') or {}).items():
        groups = rnode if isinstance(rnode, dict) else {}
        if any(isinstance(g, dict) and g for g in groups.values()):
            continue
        decided = sorted(qid for (owner, qid), q in questions.items() if owner == rkey.split('__')[0]
                         and not q.get('depends_on') and (
                             q.get('resolved_by') == 'interview'
                             or 'deployment' in (q.get('answer') or {})
                             or (q.get('_group') in ('networking', 'security') and q.get('default') is not None)))
        if decided:
            shown = ', '.join(decided[:5]) + (f" and {len(decided) - 5} more" if len(decided) > 5 else '')
            errors.append(f"resources.{rkey} records no decision, but its set decides {shown} - "
                          f"resolve the set and write its values, defaults included")

    # --- 9e. a required question that applies has a value or an open entry ------
    # A `required` question has no default: when its depends_on holds, the spec carries its
    # value or an open entry naming it - leaving it out reads as "nothing open" in the decision
    # document and the diagram, and the render meets a parameter nobody can fill. Only a
    # depends_on on a question of the same set whose value the spec records is evaluated; one
    # nothing records cannot be decided here and is left to the interview.
    def holds(cond, group_values):
        conds = cond if isinstance(cond, list) else [cond]
        for c in conds:
            if not isinstance(c, dict) or c.get('question') not in group_values:
                return False
            v = group_values[c['question']]
            if 'equals' in c and v != c['equals']:
                return False
            if 'not_equals' in c and v == c['not_equals']:
                return False
        return True

    for rkey, rnode in (get(spec, 'resources') or {}).items():
        if not isinstance(rnode, dict):
            continue
        recorded = {}
        for gid, gnode in rnode.items():
            for qid, d in (gnode.items() if isinstance(gnode, dict) else []):
                if isinstance(d, dict) and 'value' in d:
                    recorded[qid] = (gid, d['value'])
        values = {qid: v for qid, (_, v) in recorded.items()}
        for (owner, qid), q in questions.items():
            if owner != rkey.split('__')[0] or not q.get('required') or 'answer' in q or qid in recorded:
                continue
            if not q.get('depends_on') or not holds(q['depends_on'], values):
                continue
            path = f"resources.{rkey}.{q.get('_group')}.{qid}"
            if path not in open_keys and path not in open_stages:
                # a warning: specs written before this rule may lack such a value and still render
                warnings.append(f"{path} is required once {q['depends_on'].get('question') if isinstance(q['depends_on'], dict) else 'its condition'} "
                              f"holds, but the spec has neither its value nor an open entry naming it - "
                              f"a missing decision reads as nothing open")

    # --- 9f. a subnet's name is its short purpose -------------------------------
    # The render names every subnet from the convention with the spec's name as <PURPOSE>, so an
    # Azure-style name (`snet-app`) comes out as snet-<loc>-<env>-<workload>-snet-app-01. A
    # subnet that exists under such a name says so with azure_name. A warning: specs written
    # before the rule carry Azure-style names and still render.
    for rkey, rnode in (get(spec, 'resources') or {}).items():
        if rkey.split('__')[0] != 'virtual-network' or not isinstance(rnode, dict):
            continue
        listed = get(get(get(rnode, 'addressing'), 'subnets'), 'value')
        per = listed.values() if isinstance(listed, dict) else [listed]
        named = {str(s.get('name')) for lst in per if isinstance(lst, list) for s in lst
                 if isinstance(s, dict) and str(s.get('name', '')).lower().startswith('snet-') and not s.get('azure_name')}
        for name in sorted(named):
            warnings.append(f"resources.{rkey}.addressing.subnets names '{name}' - a subnet's name is its short "
                            f"purpose ('{name[5:]}'), the render builds the Azure name from the convention; "
                            f"a subnet that exists under this name carries azure_name: {name}")

    # --- 10. deployer roles ------------------------------------------------
    def filled(v):
        """A list value, or a stage map of lists, that holds at least one entry."""
        if isinstance(v, dict):
            return any(filled(x) for x in v.values())
        return bool(v)

    needs = []  # (what, accepted roles, accepted scopes, the decision that needs it)
    creates = [r for r in in_play if rg_roles.mode(dep_node, r) == 'create']
    scope = dep_value('deployment_scope')
    if creates or scope == 'subscription':
        needs.append(('a resource group is created' if creates else 'the deployment runs at subscription scope',
                      ROLES_CREATE_GROUP, ['subscription'], ['deployment.resource_groups_created'] if creates else ['deployment.deployment_scope']))
    for rkey, rnode in (get(spec, 'resources') or {}).items():
        if str(rkey).split('__')[0] == 'key-vault':
            d = get(get(rnode, 'security'), 'secret_placeholders')
            if isinstance(d, dict) and filled(d.get('value')):
                needs.append((f"'{rkey}' holds secret placeholders", ROLES_SECRETS, [rkey, 'resource_group', 'subscription'],
                              [f'resources.{rkey}.security.secret_placeholders']))
    d = get(get(spec, 'wiring'), 'role_assignments')
    if isinstance(d, dict) and filled(d.get('value')):
        needs.insert(0, ('roles are assigned', ROLES_ASSIGN, ['resource_group', 'subscription'], ['wiring.role_assignments']))

    granted = dep_value('deployer_roles')
    dr_errors = len(errors)
    if scope == 'resource_group':
        for c in creates:
            errors.append(f"resource group '{c}' is created (resource_groups_created) under deployment_scope resource_group - "
                          f"the deployment only reaches groups that exist; creating one is deployment_scope subscription")
    iso = dep_value('stage_isolation')
    if scope and iso and iso != scope:
        errors.append(f"deployment.stage_isolation is {iso}, but deployment_scope is {scope} - the isolation "
                      f"follows the scope: subscription level needs a subscription per stage, resource-group level "
                      f"separates the stages by the identities' role scope")
    if scope == 'subscription' and iso == 'resource_group':
        errors.append("deployment.deployment_scope is subscription under stage_isolation resource_group - a role on the "
                      "shared subscription reaches every stage; the scope is resource_group")
    if dep_value('stage_isolation') == 'resource_group':
        for c in creates:
            errors.append(f"resource group '{c}' is created (resource_groups_created) under stage_isolation resource_group - "
                          f"creating a group needs a role on the shared subscription, which reaches every stage; the groups "
                          f"exist beforehand")
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
