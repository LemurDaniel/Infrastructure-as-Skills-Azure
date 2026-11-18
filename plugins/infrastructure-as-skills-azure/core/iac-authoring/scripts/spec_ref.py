"""Reads a reference in a spec, shared by the checks, the diagram, the digest and the documents.

A question with `accepts: { ref: <kind> }` takes a reference, in one of two forms
(references/spec.md, the kinds in references/ref-kinds.yaml):

  {resource: <key>}                     a resource of this spec, the same in every stage
  {resource: <key>, part: <name>}       a named part of it (a subnet of the network)
  {existing: <kind>}                    one outside the spec; its id is an open: entry
  {existing: <kind>, id: {<stage>: <id>}}  one outside the spec whose id is known

A `list` question takes a list of them. Nothing else is a reference: no bare name, no
stage map around one, no name and resource group.
"""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
KINDS_FILE = os.path.join(HERE, '..', 'references', 'ref-kinds.yaml')

GUID = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
ARM_ANY = re.compile(r'^(/subscriptions/[0-9a-fA-F-]{36}(/resourceGroups/[^/]+(/providers/.+)?)?'
                     r'|/providers/Microsoft\.Management/managementGroups/[^/]+)$', re.IGNORECASE)


def load_kinds(yaml):
    """kind -> its entry of ref-kinds.yaml: `set`, or `part_of` with `listed_in` and
    `always_present` for a part, and `existing: { type, id }`."""
    with open(KINDS_FILE, encoding='utf-8') as f:
        return (yaml.safe_load(f) or {}).get('kinds') or {}


def set_of(kind):
    """The question set a `resource:` reference of this kind names: the set the part belongs
    to, the set that creates the resource, `any`, or None when the spec never creates one."""
    return (kind or {}).get('part_of') or (kind or {}).get('set')


def id_form(kind):
    """The form an id of this kind has: arm, arm_any or guid."""
    return ((kind or {}).get('existing') or {}).get('id')


def id_type(kind):
    """The ARM type an id of this kind carries, None where the form asks for none."""
    return ((kind or {}).get('existing') or {}).get('type')


def kind_of(question):
    """The kind a question references, or None when it takes no reference."""
    acc = (question or {}).get('accepts')
    if isinstance(acc, dict) and acc.get('ref'):
        return acc['ref']
    return None


def is_ref(v):
    """True for one reference in either form."""
    return isinstance(v, dict) and ('resource' in v or 'existing' in v)


def items(v):
    """The references a value holds: one, each item of a list, none for an empty value."""
    if v in (None, '', [], {}):
        return []
    return v if isinstance(v, list) else [v]


def arm_type(rid):
    """Microsoft.Network/virtualNetworks/subnets for a subnet's id; resource groups and
    subscriptions read as Microsoft.Resources/..., None for what is no resource id."""
    if not isinstance(rid, str) or not ARM_ANY.match(rid):
        return None
    parts = rid.strip('/').split('/')
    if '/providers/' in rid.lower():
        i = [p.lower() for p in parts].index('providers')
        tail = parts[i + 1:]
        if len(tail) < 3 or len(tail) % 2 == 0:
            return None
        return '/'.join([tail[0]] + tail[1::2])
    if len(parts) >= 4 and parts[2].lower() == 'resourcegroups':
        return 'Microsoft.Resources/resourceGroups'
    return 'Microsoft.Resources/subscriptions'


def id_fits(rid, kind):
    """Whether an id has the form its kind asks for."""
    form = id_form(kind)
    if form == 'guid':
        return isinstance(rid, str) and bool(GUID.match(rid))
    if form == 'arm_any':
        return arm_type(rid) is not None
    t = arm_type(rid)
    return t is not None and t.lower() == str(id_type(kind) or '').lower()


def _value(resource, path):
    group, question = path.split('.', 1)
    node = ((resource or {}).get(group) or {}).get(question)
    return node.get('value') if isinstance(node, dict) and 'value' in node else node


def part_names(resource, listed_in, always_present=None):
    """The names a resource's part question holds (`addressing.subnets`), over every stage, and
    each part it has without listing it (ref-kinds.yaml `always_present`: the private endpoint
    subnet) where no listed part carries its prefix in a stage - a listed part with that prefix
    is that part."""
    v = _value(resource, listed_in)
    lists = v if isinstance(v, dict) else {None: v}
    names, prefixes = set(), {}
    for stage, lst in lists.items():
        for item in (lst if isinstance(lst, list) else []):
            n = item.get('name') if isinstance(item, dict) else item
            if n is not None:
                names.add(str(n))
            if isinstance(item, dict) and item.get('prefix') is not None:
                prefixes.setdefault(stage, set()).add(str(item['prefix']))
    for unlisted in always_present or []:
        answer = _value(resource, unlisted['when_answered'])
        for stage, prefix in (answer.items() if isinstance(answer, dict) else [(None, answer)]):
            listed = prefixes.get(stage, set()) | prefixes.get(None, set())
            if prefix not in (None, '') and str(prefix) not in listed:
                names.add(str(unlisted['name']))
    return names


def check(path, v, kind_name, kinds, resources, environments, open_stages, open_keys):
    """The errors of one reference value at `path`, which takes references of `kind_name`."""
    errors = []
    kind = kinds.get(kind_name)
    if kind is None:
        return [f"{path} references kind '{kind_name}', which ref-kinds.yaml does not name"]
    if environments and isinstance(v, dict) and v and all(k in environments for k in v):
        return [f"{path} is a reference split by stage - a reference is one value: "
                f"{{resource: <key>}} for this spec's, {{existing: {kind_name}, id: {{<stage>: <id>}}}} for one outside it"]
    owner = set_of(kind)
    for ref in items(v):
        if not is_ref(ref):
            errors.append(f"{path} holds {ref!r}, which is no reference - {{resource: <key>}} or {{existing: {kind_name}}} (spec.md, References)")
            continue
        if 'resource' in ref and 'existing' in ref:
            errors.append(f"{path} names both resource and existing - a reference is one or the other")
            continue
        if 'resource' in ref:
            key = str(ref['resource'])
            stray = set(ref) - {'resource', 'part'}
            if stray:
                errors.append(f"{path}: a resource reference carries {', '.join(sorted(stray))} - only resource and part")
            if key not in resources:
                errors.append(f"{path} references resource '{key}', which this spec does not hold")
                continue
            if owner != 'any' and key.split('__')[0] != owner:
                where = owner or 'none - the spec never creates one, so it is existing'
                errors.append(f"{path} references '{key}', which is no {kind_name} (a {kind_name} is a resource of: {where})")
                continue
            if kind.get('part_of'):
                if not ref.get('part'):
                    errors.append(f"{path} references '{key}' without part - a {kind_name} is a part of it, named by {kind['listed_in']}")
                else:
                    names = part_names(resources.get(key), kind['listed_in'], kind.get('always_present'))
                    if names and str(ref['part']) not in names:
                        errors.append(f"{path} references part '{ref['part']}' of '{key}', which its {kind['listed_in']} does not name ({', '.join(sorted(names))})")
            elif 'part' in ref:
                errors.append(f"{path} names a part, but a {kind_name} is a whole resource")
        else:
            if ref['existing'] != kind_name:
                errors.append(f"{path} is existing: {ref['existing']}, but its question takes a {kind_name}")
            stray = set(ref) - {'existing', 'id'}
            if stray:
                errors.append(f"{path}: an existing reference carries {', '.join(sorted(stray))} - only existing and id, "
                              f"never a name or a resource group")
            ids = ref.get('id')
            if ids is None:
                if path not in open_keys:
                    errors.append(f"{path} references an existing {kind_name} with no id and no open entry - "
                                  f"the id goes into the spec per stage, or an open: entry names who supplies it")
                continue
            if not isinstance(ids, dict) or not all(k in environments for k in ids):
                errors.append(f"{path}: the id of an existing reference is a map keyed by stage ({', '.join(environments)})")
                continue
            for stage, rid in ids.items():
                if not id_fits(rid, kind):
                    form = {'guid': 'an object id (GUID)', 'arm_any': 'a resource id'}.get(id_form(kind), f"the id of a {id_type(kind)}")
                    errors.append(f"{path} (stage {stage}) is '{rid}', which is not {form}")
            for e in environments:
                if e not in ids and e not in open_stages.get(path, set()) and path not in open_keys:
                    errors.append(f"{path} has no id for stage '{e}' and no open entry naming it")
    return errors


def resource_keys(v):
    """The resource keys a value references, in order (its parts left out)."""
    return [str(r['resource']) for r in items(v) if isinstance(r, dict) and 'resource' in r]


def label(ref):
    """What a reference reads as for a person: the key and part, or the existing resource's
    name from its id, or the kind for one whose id is still open."""
    if not isinstance(ref, dict):
        return None
    if 'resource' in ref:
        return str(ref.get('part') or ref['resource'])
    ids = ref.get('id') if isinstance(ref.get('id'), dict) else {}
    rid = ids.get('production') or next(iter(ids.values()), None)
    if isinstance(rid, str) and rid.strip('/'):
        return rid.rstrip('/').rsplit('/', 1)[-1]
    return None
