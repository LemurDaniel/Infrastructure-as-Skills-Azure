"""Resource group roles per scheme, read from references/resource-group-roles.yaml.

One reader for the spec check, the diagram and the decision document, so a scheme means the
same thing in all three. `deployment.resource_group_scheme` picks the scheme:
`concern` (the default, and what a spec without the key means), `lifecycle`, `protection`
(fixed tables), or `component`, whose parts are the design's: the foundation kinds go to
`shared`, every other resource names its part in `placement.resource_group`. Which groups exist
is derived here (`groups`), never recorded in the spec.

Import it by path - the scripts live in different skills:

    sys.path.insert(0, os.path.join(<core>, 'iac-rendering', 'scripts'))
    import rg_roles
"""

import os

ROLES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'references', 'resource-group-roles.yaml')
SCHEMES = ['concern', 'lifecycle', 'protection', 'component']
FALLBACK = {'roles': ['main', 'network', 'data', 'application', 'observability', 'security'], 'kinds': {}}


def load(yaml):
    """The parsed table; the concern roles without kinds when the file cannot be read."""
    try:
        with open(ROLES_FILE, encoding='utf-8') as f:
            return yaml.safe_load(f) or FALLBACK
    except (OSError, yaml.YAMLError):
        return FALLBACK


def value(deployment, key):
    d = (deployment or {}).get(key) if isinstance(deployment, dict) else None
    return d.get('value') if isinstance(d, dict) else d


def has_main(deployment):
    """Whether the deployment has a main group: always, unless resource_group_layout is split."""
    return value(deployment, 'resource_group_layout') != 'split'


def created(deployment):
    """The groups the render creates: `resource_groups_created`, [] when it is absent."""
    v = value(deployment, 'resource_groups_created')
    return [r for r in v if isinstance(r, str)] if isinstance(v, list) else []


def mode(deployment, role):
    """`create` for a group in resource_groups_created, `existing` for every other: the list is
    the record, no mode per group is written."""
    return 'create' if role in created(deployment) else 'existing'


def scheme_of(deployment):
    """The scheme a spec's deployment block names; `concern` when it names none."""
    v = value(deployment, 'resource_group_scheme')
    return v if v in SCHEMES else 'concern'


def table(data, scheme):
    """{role: [kinds]} of a scheme; for `component` only `shared` has kinds."""
    if scheme in ('lifecycle', 'protection'):
        return (data.get(scheme) or {}).get('kinds') or {}
    if scheme == 'component':
        source = ((data.get('component') or {}).get('shared_from')) or 'foundation'
        return {'shared': ((data.get('lifecycle') or {}).get('kinds') or {}).get(source) or []}
    return data.get('kinds') or {}


def placement(node):
    """The role a resource's `placement.resource_group` names, or None."""
    p = ((node or {}).get('placement') or {}).get('resource_group') if isinstance(node, dict) else None
    v = p.get('value') if isinstance(p, dict) else p
    return v if isinstance(v, str) and v else None


def roles(data, scheme, resources=None, deployment=None):
    """The roles a scheme can split off (never `main`); `component`: `shared` and the parts -
    those `resource_group_components` lists, else those the resources are placed in."""
    if scheme == 'component':
        parts = value(deployment, 'resource_group_components') or []
        if not parts and isinstance(resources, dict):
            parts = [placement(n) for n in resources.values()]
        out = ['shared']
        for p in parts:
            if p and p not in out and p != 'main':
                out.append(p)
        return out
    listed = (data.get(scheme) or {}).get('roles') if scheme in ('lifecycle', 'protection') else data.get('roles')
    return [r for r in (listed or list(table(data, scheme))) if r != 'main']


def groups(data, deployment, resources):
    """The roles with a group of their own, derived and never recorded: none under a single
    layout; under a split every role of the scheme that a resource of the spec is in - its
    `placement.resource_group`, else its kind's role - in the scheme's order. A role a
    placement names that the scheme does not have is left out; check_spec.py names it."""
    if value(deployment, 'resource_group_layout') != 'split':
        return []
    scheme = scheme_of(deployment)
    order = roles(data, scheme, resources)
    used = set()
    for key, node in (resources or {}).items():
        role = placement(node) or role_of(data, scheme, str(key).split('__')[0])
        if role:
            used.add(role)
    return [r for r in order if r in used]


def role_of(data, scheme, kind):
    """The role a kind belongs to under a scheme; `main` when the scheme does not place it, None
    for a kind that is deployed with the resource it serves (`attached`) and, under `component`,
    for a kind that is not shared - its part is the resource's placement."""
    if kind in (data.get('attached') or []):
        return None
    for role, kinds in table(data, scheme).items():
        if kind in (kinds or []):
            return role
    return None if scheme == 'component' else 'main'
