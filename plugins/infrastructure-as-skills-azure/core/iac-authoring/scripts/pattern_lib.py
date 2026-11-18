"""Reads a pattern, shared by check_pattern.py, apply_pattern.py, check_spec.py and the digest.

A pattern (references/pattern-format.md) is data: `patterns/<id>/pattern.yaml` names the
parts of a system, the questions only the pattern asks, the answers it gives in the parts'
question sets, and the wiring between the parts. Which parts, answers and wiring lines hold
depends on conditions (`when`), so everything that reads a pattern reads it **resolved**:
`resolve()` turns the file plus the answers into the parts, pre-answers and wiring of one
variant, and `variants()` lists every variant the conditions can produce. One reader, so the
check, the interview and the spec check cannot disagree on what a pattern says.
"""

import itertools
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
PATTERNS = os.path.join(PLUGIN, 'patterns')
ROLES_FILE = os.path.join(HERE, '..', 'references', 'built-in-roles.yaml')

ACTORS = ('users', 'internet')              # and external:<name>
APP_KINDS = ('app-service', 'function-app', 'container-apps')
IDENTITY_KIND = 'user-assigned-identity'
OPERATORS = ('equals', 'not_equals', 'contains')
# Roles that let an identity read a secret a reference resolves.
SECRET_READERS = ('Key Vault Secrets User', 'Key Vault Secrets Officer', 'Key Vault Administrator')


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def pattern_ids():
    """The ids of the patterns the plugin ships: every directory holding a pattern.yaml."""
    if not os.path.isdir(PATTERNS):
        return []
    return sorted(d for d in os.listdir(PATTERNS)
                  if os.path.isfile(os.path.join(PATTERNS, d, 'pattern.yaml')))


def path_of(pattern):
    """A pattern id, directory or file to its pattern.yaml, or None."""
    for p in (pattern, os.path.join(pattern, 'pattern.yaml'), os.path.join(PATTERNS, pattern, 'pattern.yaml')):
        if os.path.isfile(p):
            return os.path.abspath(p)
    return None


def load(yaml, pattern):
    """The parsed pattern.yaml of an id, a directory or a file; None when there is none."""
    p = path_of(pattern)
    if not p:
        return None
    with open(p, encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_roles(yaml):
    """(Azure RBAC role names, data-plane role names) from built-in-roles.yaml."""
    with open(ROLES_FILE, encoding='utf-8') as f:
        doc = yaml.safe_load(f) or {}
    return set(doc.get('roles') or {}), set(doc.get('data_plane') or {})


def load_renamed_roles(yaml):
    """{former name: current name} of the roles Microsoft renamed."""
    with open(ROLES_FILE, encoding='utf-8') as f:
        return dict((yaml.safe_load(f) or {}).get('renamed') or {})


def kind(key):
    """The question set of a resource key: `app-service` for `app-service__chat`."""
    return str(key).split('__')[0]


def is_actor(name):
    return name in ACTORS or str(name).startswith('external:')


def wording(entry, language):
    """One line in the language asked for, English where it is missing."""
    if isinstance(entry, dict):
        return entry.get(language) or entry.get('en') or ''
    return '' if entry is None else str(entry)


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------

def conditions(when):
    """A `when` as a list of conditions; one condition and a list of them read the same."""
    if when is None:
        return []
    return when if isinstance(when, list) else [when]


def holds(when, answers):
    """Whether every condition of a `when` holds for these answers to the pattern's asks."""
    for c in conditions(when):
        if not isinstance(c, dict):
            return False
        value = answers.get(c.get('ask'))
        if 'equals' in c and value != c['equals']:
            return False
        if 'not_equals' in c and value == c['not_equals']:
            return False
        if 'contains' in c and not (isinstance(value, list) and c['contains'] in value):
            return False
    return True


def ask_defaults(pattern):
    return {a['id']: a.get('default') for a in (pattern.get('asks') or []) if isinstance(a, dict) and a.get('id')}


def variants(pattern):
    """Every set of answers the pattern's conditions tell apart: each value of each enum or
    bool ask. An ask of another type keeps its default - no condition enumerates free text."""
    axes = []
    for a in pattern.get('asks') or []:
        if not isinstance(a, dict) or not a.get('id'):
            continue
        if a.get('type') == 'bool':
            values = [True, False]
        elif a.get('type') == 'enum' and isinstance(a.get('accepts'), list):
            values = list(a['accepts'])
        else:
            values = [a.get('default')]
        axes.append([(a['id'], v) for v in values])
    for combo in itertools.product(*axes):
        yield dict(combo)


# ---------------------------------------------------------------------------
# Resolving one variant
# ---------------------------------------------------------------------------

def resolve(pattern, answers=None):
    """One variant of a pattern, conditions applied:

        answers      every ask's value (the given one, else its default)
        parts        {key: part} of the parts that exist
        pre_answers  {owner: {question id: entry}} for those parts and `deployment`
        wiring       {access | role_assignments | secrets: [line, ...]} without `when`
    """
    full = ask_defaults(pattern)
    full.update(answers or {})

    parts = {k: p for k, p in (pattern.get('parts') or {}).items()
             if holds((p or {}).get('when'), full)}

    pre = {}
    for owner, entries in (pattern.get('pre_answers') or {}).items():
        if owner != 'deployment' and owner not in parts:
            continue
        for qid, entry in (entries or {}).items():
            # one entry, or several that differ by `when`: the first that holds answers
            for e in entry if isinstance(entry, list) else [entry]:
                if isinstance(e, dict) and holds(e.get('when'), full):
                    pre.setdefault(owner, {})[qid] = e
                    break

    wiring = {}
    for section, lines in (pattern.get('wiring') or {}).items():
        kept = [{k: v for k, v in line.items() if k != 'when'} for line in (lines or [])
                if isinstance(line, dict) and holds(line.get('when'), full)]
        if kept:
            wiring[section] = kept
    return {'answers': full, 'parts': parts, 'pre_answers': pre, 'wiring': wiring}


def set_question(questions, key, qid):
    """The question `qid` of the set a resource key (or `deployment`) belongs to."""
    return questions.get((key if key == 'deployment' else kind(key), qid))


def identity_of(key, resolved, questions):
    """How a part authenticates: 'identity' (it is a user-assigned identity), the effective
    value of its set's `managed_identity` question (the pre-answer, else the default), or
    None for a set that has no identity of its own."""
    if kind(key) == IDENTITY_KIND:
        return 'identity'
    q = set_question(questions, key, 'managed_identity')
    if q is None:
        return None
    entry = (resolved['pre_answers'].get(key) or {}).get('managed_identity')
    return entry.get('value') if isinstance(entry, dict) else q.get('default')


def principals_of(key, resolved, questions):
    """The parts whose identity a part acts with: itself when system-assigned, the
    identities its `user_assigned_identity_ids` pre-answer names when user-assigned."""
    mode = identity_of(key, resolved, questions)
    if mode in ('identity', 'system_assigned'):
        return [key]
    if mode == 'user_assigned':
        entry = (resolved['pre_answers'].get(key) or {}).get('user_assigned_identity_ids') or {}
        value = entry.get('value') if isinstance(entry, dict) else None
        return [r.get('resource') for r in (value if isinstance(value, list) else [value])
                if isinstance(r, dict) and r.get('resource')]
    return []


def users_of(identity, resolved, questions):
    """The parts that act with an identity part: those whose identities list names it."""
    return [k for k in resolved['parts'] if k != identity and identity in principals_of(k, resolved, questions)]


# ---------------------------------------------------------------------------
# Applying: a variant as the pattern's share of a spec
# ---------------------------------------------------------------------------

def _staged(value, question, environments):
    """A per-stage question's value as a map keyed by stage; a reference stays one value."""
    acc = (question or {}).get('accepts')
    is_reference = isinstance(acc, dict) and acc.get('ref')
    if environments and (question or {}).get('per_environment') and not is_reference and value not in (None, '', [], {}):
        return {e: value for e in environments}
    return value


def apply(pattern, questions, answers=None, language='en', environments=None, selected='stated'):
    """The pattern's share of an infra-spec.yaml for one variant: `pattern`, the
    deployment and resource decisions it pre-answers (source: pattern) and the wiring.
    Nothing else - what the pattern does not answer is the interview's and the sets'."""
    given = dict(answers or {})
    resolved = resolve(pattern, given)

    spec = {'pattern': {'id': {'value': pattern.get('id'), 'source': selected}}}
    if resolved['answers']:
        spec['pattern']['answers'] = {
            aid: {'value': v, 'source': 'asked' if aid in given else 'default'}
            for aid, v in resolved['answers'].items()}

    dep = {qid: {'value': e.get('value'), 'source': 'pattern'}
           for qid, e in (resolved['pre_answers'].get('deployment') or {}).items()}
    if dep:
        spec['deployment'] = dep

    resources = {}
    for key, part in resolved['parts'].items():
        node = {'meta': {'purpose': {'value': wording((part or {}).get('purpose'), language), 'source': 'pattern'}}}
        for qid, entry in (resolved['pre_answers'].get(key) or {}).items():
            q = set_question(questions, key, qid) or {}
            node.setdefault(q.get('_group') or 'unknown', {})[qid] = {
                'value': _staged(entry.get('value'), q, environments), 'source': 'pattern'}
        resources[key] = node
    spec['resources'] = resources

    wiring = {}
    for section, lines in resolved['wiring'].items():
        out = []
        for line in lines:
            line = dict(line)
            if 'label' in line:
                line['label'] = wording(line['label'], language)
            out.append(line)
        wiring[section] = {'value': out, 'source': 'pattern'}
    if wiring:
        spec['wiring'] = wiring
    return spec, resolved
