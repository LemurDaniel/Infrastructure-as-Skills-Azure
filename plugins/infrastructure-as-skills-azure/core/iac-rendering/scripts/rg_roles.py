"""Resource group roles per scheme, read from references/resource-group-roles.yaml.

One reader for the spec check, the diagram, the decision document and the name list, so a
scheme means the same thing in all four. `deployment.resource_group_scheme` picks the scheme:
`concern` (the default, and what a spec without the key means), `lifecycle`, or
`resource_type`, where a kind's role is its set name and no table is needed.

Import it by path - the scripts live in different skills:

    sys.path.insert(0, os.path.join(<core>, 'iac-rendering', 'scripts'))
    import rg_roles
"""

import os

ROLES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'references', 'resource-group-roles.yaml')
SCHEMES = ['concern', 'lifecycle', 'resource_type']
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
    """Whether the deployment has a main group: always, unless resource_group_layout is split.
    A spec written before the layout key keeps its main group beside the split roles."""
    return value(deployment, 'resource_group_layout') != 'split'


def scheme_of(deployment):
    """The scheme a spec's deployment block names; `concern` when it names none."""
    v = value(deployment, 'resource_group_scheme')
    return v if v in SCHEMES else 'concern'


def table(data, scheme):
    """{role: [kinds]} of a scheme; empty for `resource_type`."""
    if scheme == 'lifecycle':
        return (data.get('lifecycle') or {}).get('kinds') or {}
    if scheme == 'resource_type':
        return {}
    return data.get('kinds') or {}


def roles(data, scheme, resource_keys=()):
    """The roles a scheme can split off (never `main`). `resource_type`: the set names present."""
    if scheme == 'resource_type':
        attached = data.get('attached') or []
        return list(dict.fromkeys(k for k in (str(r).split('__')[0] for r in resource_keys) if k not in attached))
    listed = (data.get('lifecycle') or {}).get('roles') if scheme == 'lifecycle' else data.get('roles')
    return [r for r in (listed or list(table(data, scheme))) if r != 'main']


def role_of(data, scheme, kind):
    """The role a kind belongs to under a scheme; `main` when the scheme does not place it, None
    for a kind that is deployed with the resource it serves (`attached`)."""
    if kind in (data.get('attached') or []):
        return None
    if scheme == 'resource_type':
        return kind
    for role, kinds in table(data, scheme).items():
        if kind in (kinds or []):
            return role
    return 'main'
