#!/usr/bin/env python3
"""Validates patterns against the pattern format.

Read-only. A pattern is trusted more than a question set - its answers are applied without
being asked - so what references/pattern-format.md promises is checked, not assumed:

  1. The envelope: schema_version, an `id` that is the directory's name, `title` and
     `summary` in en and de, `selects_when` signals, no unknown field, and a row in
     patterns/routing.md that leads to it.
  2. Parts: every key names a question set (`<set>` or `<set>__<instance>`) and carries a
     `purpose` in en and de.
  3. Asks: each is an interview question in the question-set format (ask, type, accepts,
     why, plain, topic) with a default - the pattern applies before the answer - and an
     id the deployment set does not use.
  4. Pre-answers: the owner is a part or `deployment`; the question exists in that set and
     the value is one it accepts, with a `why`. Never a question the customer is asked,
     one a requirement derives, or one that inherits a deployment decision - a pattern
     answers defaults and required values, never the customer or the posture. A reference
     is `{ resource: <part> }` naming a part of a set the kind allows.
  5. Conditions: every `when` names an ask of the pattern, one operator, and a value that
     ask can take.
  6. Wiring, for **every variant** the conditions can produce (each value of each enum or
     bool ask):
       - an access line runs between parts that exist or actors (users, internet,
         external:<name>), with a label in en and de where it has one;
       - a role assignment goes from a part that has an identity of its own (a
         user-assigned identity, or a system-assigned one - never a part whose identity is
         user-assigned or none) to a part that exists, names a role of
         built-in-roles.yaml (a data-plane role only on its own service), and is explained
         by an access line from the part that acts with that identity;
       - a secret names an application and a key vault that exist, a secret the vault's
         `secret_placeholders` pre-answer creates, and an identity of the application
         holds a role on the vault that reads secrets;
       - a reference in a pre-answer names a part that exists in that variant, and a
         user-assigned identity is used by a part.
  7. `composition`, where present: a known granularity, unique module ids, every module
     containing parts of the pattern only.

Needs PyYAML (pip install pyyaml). Without it the script says so and exits 2.

Usage:
    python3 check_pattern.py [<pattern>...]

A pattern is an id under patterns/, a pattern directory or a pattern.yaml. With none,
every pattern the plugin ships. Exit 0 clean, 1 violations, 2 could not check.
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pattern_lib as lib  # noqa: E402 - the one reader of a pattern
import check_question_set  # noqa: E402 - an ask is a question in the question-set format
import check_spec  # noqa: E402 - the question index of the plugin's sets
import spec_ref  # noqa: E402 - what a reference kind accepts

KNOWN_TOP = {'schema_version', 'id', 'title', 'summary', 'selects_when', 'parts', 'asks', 'pre_answers',
             'wiring', 'composition', 'boundaries'}
KNOWN_PART = {'purpose', 'when'}
KNOWN_PRE = {'value', 'why', 'when'}
WIRING = {'access': {'from', 'to', 'label', 'when'},
          'role_assignments': {'from', 'to', 'role', 'when'},
          'secrets': {'app', 'setting', 'vault', 'secret_name', 'when'}}
REQUIRED_WIRING = {'access': ('from', 'to'), 'role_assignments': ('from', 'to', 'role'),
                   'secrets': ('app', 'setting', 'vault', 'secret_name')}
GRANULARITIES = ('single', 'per-concern', 'per-resource', 'per-family')
LANGUAGES = ('en', 'de')
# The service a data-plane role belongs to: it is assigned through that service, nowhere else.
DATA_PLANE_SETS = {'Cosmos DB Built-in Data Reader': 'cosmos-db', 'Cosmos DB Built-in Data Contributor': 'cosmos-db'}

say, ok, bad, warn = check_question_set.say, check_question_set.ok, check_question_set.bad, check_question_set.warn


def both_languages(entry):
    return isinstance(entry, dict) and all(isinstance(entry.get(lang), str) and entry[lang].strip() for lang in LANGUAGES)


def describe(answers):
    """A variant in words, for a message: `sign_in=company_accounts, history=True`."""
    return ', '.join(f"{k}={v}" for k, v in answers.items()) or 'no ask'


def check_envelope(doc, path, err):
    for k in doc:
        if k not in KNOWN_TOP:
            err(f"unknown top-level field '{k}'")
    if doc.get('schema_version') != 1:
        err(f"schema_version is {doc.get('schema_version')!r}; the pattern format is version 1")
    pid = doc.get('id')
    folder = os.path.basename(os.path.dirname(path))
    if not pid or not re.match(r'^[a-z][a-z0-9-]*$', str(pid)):
        err(f"id {pid!r} is not a short lowercase name (ai-chat-rag)")
    elif pid != folder:
        err(f"id '{pid}' is not its directory's name '{folder}' - the routing table and the spec name the directory")
    for field in ('title', 'summary'):
        if not both_languages(doc.get(field)):
            err(f"{field} needs one line in each of {', '.join(LANGUAGES)} - the proposal is said in the customer's language")
    signals = doc.get('selects_when')
    if not isinstance(signals, list) or not signals or not all(isinstance(s, str) and s.strip() for s in signals):
        err('selects_when is missing - the request signals that choose this pattern, one phrase each')
    if 'boundaries' in doc and not (isinstance(doc['boundaries'], list) and all(isinstance(b, str) for b in doc['boundaries'])):
        err('boundaries must be a list of sentences')
    routing = os.path.join(os.path.dirname(os.path.dirname(path)), 'routing.md')
    if not os.path.isfile(routing):
        err('no routing.md beside the pattern directories - the interview finds a pattern through it')
    elif pid:
        with open(routing, encoding='utf-8') as f:
            if f"{pid}/pattern.yaml" not in f.read():
                err(f"routing.md has no row leading to {pid}/pattern.yaml - the pattern is unreachable")


def check_when(when, where, asks, err):
    for c in lib.conditions(when):
        ops = [k for k in lib.OPERATORS if k in c] if isinstance(c, dict) else []
        if not isinstance(c, dict) or 'ask' not in c or len(ops) != 1 or set(c) - {'ask'} - set(lib.OPERATORS):
            err(f"{where}: when must be {{ ask: <id>, {' | '.join(lib.OPERATORS)}: <value> }}, or a list of them")
            continue
        qid, value = c['ask'], c[ops[0]]
        q = asks.get(qid)
        if q is None:
            err(f"{where}: when names ask '{qid}', which the pattern does not ask")
            continue
        accepts = q.get('accepts') if isinstance(q.get('accepts'), list) else None
        if ops[0] == 'contains' and q.get('type') != 'list':
            err(f"{where}: when {qid} contains needs a list ask, but {qid} is {q.get('type')}")
        elif q.get('type') == 'bool' and not isinstance(value, bool):
            err(f"{where}: when {qid} {ops[0]} {value!r}, but {qid} is a bool")
        elif accepts is not None and value not in accepts:
            err(f"{where}: when {qid} {ops[0]} '{value}', which {qid} cannot take (accepts {accepts})")


def check_asks(doc, questions, rel):
    """The asks as a question set, through the question-set check; returns (errors, by id)."""
    errors = []
    asks = doc.get('asks') or []
    if not isinstance(asks, list):
        return [f"{rel}: asks must be a list of questions"], {}
    by_id = {a.get('id'): a for a in asks if isinstance(a, dict)}
    if not asks:
        return errors, by_id
    # `renders` is the deployment set's field; an ask renders nothing itself - its answer
    # selects parts, answers and wiring - so the shared check is given a stand-in.
    pseudo = {'schema_version': 1, 'scope': 'deployment', 'title': 'pattern asks',
              'groups': [{'id': 'asks', 'title': 'Asks', 'questions': [dict(a, renders='the pattern') for a in asks if isinstance(a, dict)]}]}
    e, _, _ = check_question_set.check_set(rel, pseudo, None, rel)
    errors.extend(e)
    for a in asks:
        if not isinstance(a, dict):
            errors.append(f"{rel}: an ask is not a mapping")
            continue
        aid = a.get('id')
        if 'renders' in a:
            errors.append(f"{rel}: asks.{aid}: an ask has no renders - its answer selects parts, answers and wiring")
        if a.get('resolved_by') != 'interview':
            errors.append(f"{rel}: asks.{aid}: an ask is put to the customer - resolved_by: interview with a topic")
        if 'default' not in a:
            errors.append(f"{rel}: asks.{aid}: an ask needs a default - the pattern is applied before the answer, and silence must give a system")
        if ('deployment', aid) in questions:
            errors.append(f"{rel}: asks.{aid}: the deployment set already asks '{aid}' - one batch, one id")
    return errors, by_id


def check_pre_answers(doc, questions, kinds, asks, err):
    parts = doc.get('parts') or {}
    pre = doc.get('pre_answers') or {}
    if not isinstance(pre, dict):
        err('pre_answers must map a part (or deployment) to its answers')
        return
    for owner, entries in pre.items():
        if owner != 'deployment' and owner not in parts:
            err(f"pre_answers.{owner}: not a part of the pattern")
            continue
        if not isinstance(entries, dict):
            err(f"pre_answers.{owner}: must map question ids to {{ value, why }}")
            continue
        for qid, entry in entries.items():
            where = f"pre_answers.{owner}.{qid}"
            q = lib.set_question(questions, owner, qid)
            if q is None:
                err(f"{where}: the {'deployment' if owner == 'deployment' else lib.kind(owner)} set has no question '{qid}'")
                continue
            if q.get('resolved_by') == 'interview':
                err(f"{where}: the customer is asked this - a pattern never answers for them")
            answer = q.get('answer') or {}
            if 'question' in answer:
                err(f"{where}: derived from the customer's answer to {answer['question']} - a pattern never overrides a requirement")
            elif 'deployment' in answer or 'context' in answer:
                err(f"{where}: inherits {'deployment.' + str(answer.get('deployment')) if 'deployment' in answer else 'context.' + str(answer.get('context'))} - "
                    f"one decision per system, not the pattern's")
            options = entry if isinstance(entry, list) else [entry]
            if isinstance(entry, list) and not all(isinstance(e, dict) and e.get('when') for e in entry):
                err(f"{where}: several answers need a when each - the first that holds is taken")
            for e in options:
                if not isinstance(e, dict) or 'value' not in e:
                    err(f"{where}: must be {{ value, why }}")
                    continue
                extra = set(e) - KNOWN_PRE
                if extra:
                    err(f"{where}: unknown key(s) {sorted(extra)}")
                if len(str(e.get('why') or '').strip()) < 40:
                    err(f"{where}: why is missing or one phrase - say what in this system makes the answer follow")
                check_when(e.get('when'), where, asks, err)
                check_value(where, e['value'], q, parts, kinds, err)


def check_value(where, value, q, parts, kinds, err):
    """A pre-answer's value against its question: the kind, the accepted values, a reference."""
    qtype = q.get('type')
    ref_kind = spec_ref.kind_of(q)
    if ref_kind:
        allowed = (kinds.get(ref_kind) or {}).get('sets')
        refs = spec_ref.items(value)
        if qtype == 'list' and not isinstance(value, list):
            err(f"{where}: a list of references, each {{ resource: <part> }}")
        for r in refs:
            if not isinstance(r, dict) or set(r) - {'resource', 'part'} or not r.get('resource'):
                err(f"{where}: a reference in a pattern is {{ resource: <part> }} - a pattern knows no resource outside itself")
            elif r['resource'] not in parts:
                err(f"{where}: references '{r['resource']}', which is not a part of the pattern")
            elif isinstance(allowed, list) and lib.kind(r['resource']) not in allowed:
                err(f"{where}: references '{r['resource']}', but a {ref_kind} is one of {', '.join(allowed) or 'no set of the plugin'}")
        return
    if not check_question_set.kind_matches(qtype, value):
        err(f"{where}: value {value!r} is not a {qtype}")
        return
    accepts = q.get('accepts') if isinstance(q.get('accepts'), list) else None
    if accepts is not None:
        off = [v for v in (value if qtype == 'list' else [value]) if v not in accepts]
        if off:
            err(f"{where}: {off} is not in the question's accepts {accepts}")


def check_static_wiring(doc, asks, err):
    wiring = doc.get('wiring') or {}
    if not isinstance(wiring, dict):
        err('wiring must hold access, role_assignments and secrets')
        return
    for section, lines in wiring.items():
        if section not in WIRING:
            err(f"wiring.{section}: not one of {', '.join(WIRING)}")
            continue
        if not isinstance(lines, list):
            err(f"wiring.{section}: must be a list")
            continue
        for i, line in enumerate(lines):
            where = f"wiring.{section}[{i}]"
            if not isinstance(line, dict):
                err(f"{where}: not a mapping")
                continue
            extra = set(line) - WIRING[section]
            if extra:
                err(f"{where}: unknown key(s) {sorted(extra)}")
            missing = [k for k in REQUIRED_WIRING[section] if not isinstance(line.get(k), str) or not line.get(k)]
            if missing:
                err(f"{where}: {', '.join(missing)} missing")
            if 'label' in line and not both_languages(line['label']):
                err(f"{where}: label needs one line in each of {', '.join(LANGUAGES)}")
            check_when(line.get('when'), where, asks, err)


def check_variant(doc, resolved, questions, rbac, data_plane, err):
    """What must hold in one variant: the wiring only names what exists there."""
    parts, wiring, pre = resolved['parts'], resolved['wiring'], resolved['pre_answers']

    for owner, entries in pre.items():
        for qid, entry in entries.items():
            q = lib.set_question(questions, owner, qid) or {}
            if spec_ref.kind_of(q):
                for r in spec_ref.items(entry.get('value')):
                    if isinstance(r, dict) and r.get('resource') and r['resource'] not in parts:
                        err(f"pre_answers.{owner}.{qid} references '{r['resource']}', which does not exist")

    access = wiring.get('access') or []
    for a in access:
        for side in ('from', 'to'):
            name = a.get(side)
            if isinstance(name, str) and name not in parts and not lib.is_actor(name):
                err(f"wiring.access {a.get('from')} -> {a.get('to')}: '{name}' is neither a part that exists nor users, internet or external:<name>")
    reaches = {(a.get('from'), a.get('to')) for a in access}

    roles = wiring.get('role_assignments') or []
    for r in roles:
        src, dst, role = r.get('from'), r.get('to'), r.get('role')
        where = f"wiring.role_assignments {src} -> {dst} ({role})"
        if dst not in parts:
            err(f"{where}: '{dst}' does not exist")
        if role in data_plane:
            if dst in parts and DATA_PLANE_SETS.get(role) != lib.kind(dst):
                err(f"{where}: a role of {DATA_PLANE_SETS.get(role)}'s own role model, not assignable on a {lib.kind(dst)}")
        elif role not in rbac:
            err(f"{where}: not a built-in role (built-in-roles.yaml) - a misspelt role fails at the first apply")
        if src not in parts:
            err(f"{where}: '{src}' does not exist")
            continue
        mode = lib.identity_of(src, resolved, questions)
        if mode == 'user_assigned':
            err(f"{where}: {src} acts with a user-assigned identity - the role goes to that identity "
                f"({', '.join(lib.principals_of(src, resolved, questions)) or 'none named in user_assigned_identity_ids'})")
        elif mode not in ('identity', 'system_assigned'):
            err(f"{where}: {src} has no identity of its own (managed_identity: {mode}) - nothing could hold the role")
        actors = [src] + (lib.users_of(src, resolved, questions) if lib.kind(src) == lib.IDENTITY_KIND else [])
        if dst in parts and not any((a, dst) in reaches for a in actors):
            err(f"{where}: no access line from {' or '.join(actors)} to {dst} - a role nobody's connection explains")

    for key in parts:
        if lib.kind(key) == lib.IDENTITY_KIND and not lib.users_of(key, resolved, questions):
            err(f"{key}: no part names it in user_assigned_identity_ids - an identity nothing acts with")

    for s in wiring.get('secrets') or []:
        app, vault, secret = s.get('app'), s.get('vault'), s.get('secret_name')
        where = f"wiring.secrets {app}.{s.get('setting')}"
        if app not in parts or lib.kind(app) not in lib.APP_KINDS:
            err(f"{where}: '{app}' is not an application that exists ({', '.join(lib.APP_KINDS)})")
            continue
        if vault not in parts or lib.kind(vault) != 'key-vault':
            err(f"{where}: '{vault}' is not a key vault that exists")
            continue
        placeholders = ((pre.get(vault) or {}).get('secret_placeholders') or {}).get('value') or []
        if secret not in placeholders:
            err(f"{where}: secret '{secret}' is not in pre_answers.{vault}.secret_placeholders - the reference resolves to nothing at the first start")
        principals = lib.principals_of(app, resolved, questions)
        if not any(r.get('from') in principals and r.get('to') == vault and r.get('role') in lib.SECRET_READERS for r in roles):
            err(f"{where}: no identity of {app} ({', '.join(principals) or 'it has none'}) holds a secret-reading role on {vault}")


def check_composition(doc, err):
    comp = doc.get('composition')
    if comp is None:
        return
    if not isinstance(comp, dict):
        err('composition must hold granularity and modules')
        return
    if comp.get('granularity') not in GRANULARITIES:
        err(f"composition.granularity {comp.get('granularity')!r} is not one of {', '.join(GRANULARITIES)}")
    modules = comp.get('modules') or []
    ids = [m.get('id') for m in modules if isinstance(m, dict)]
    dupes = sorted({i for i in ids if ids.count(i) > 1}, key=str)
    if dupes:
        err(f"composition: duplicate module id(s) {', '.join(map(str, dupes))}")
    parts = doc.get('parts') or {}
    for m in modules:
        for c in (m.get('contains') or []) if isinstance(m, dict) else []:
            if c not in parts:
                err(f"composition.{m.get('id')} contains '{c}', which is not a part of the pattern")
        for n in (m.get('needs') or []) if isinstance(m, dict) else []:
            if n not in ids:
                err(f"composition.{m.get('id')} needs '{n}', which is not a module of the pattern")


def check_pattern(path, doc, questions, kinds, rbac, data_plane):
    """(errors, number of variants checked) for one parsed pattern.yaml."""
    rel = os.path.relpath(path, lib.PLUGIN).replace(os.sep, '/') if path.startswith(lib.PLUGIN) else path
    errors = []

    def err(text):
        message = f"{rel}: {text}"
        if message not in errors:
            errors.append(message)

    if not isinstance(doc, dict):
        return [f"{rel}: does not parse as a mapping"], 0
    check_envelope(doc, path, err)

    parts = doc.get('parts')
    if not isinstance(parts, dict) or not parts:
        err('parts is missing or empty - a pattern names the resources of its system')
        return errors, 0
    sets = {owner for owner, _ in questions if owner != 'deployment'}
    for key, part in parts.items():
        if lib.kind(key) not in sets:
            err(f"parts.{key}: no question set '{lib.kind(key)}' - a pattern composes what the plugin can interview")
        if not isinstance(part, dict) or not both_languages(part.get('purpose')):
            err(f"parts.{key}: purpose needs one line in each of {', '.join(LANGUAGES)} - what the part is for, in the customer's words")
        for k in (part or {}) if isinstance(part, dict) else []:
            if k not in KNOWN_PART:
                err(f"parts.{key}: unknown key '{k}'")

    ask_errors, asks = check_asks(doc, questions, rel)
    for e in ask_errors:
        if e not in errors:
            errors.append(e)
    for key, part in parts.items():
        if isinstance(part, dict):
            check_when(part.get('when'), f"parts.{key}", asks, err)
    check_pre_answers(doc, questions, kinds, asks, err)
    check_static_wiring(doc, asks, err)
    check_composition(doc, err)
    if errors:
        return errors, 0   # a variant of a malformed pattern proves nothing

    count = 0
    for answers in lib.variants(doc):
        count += 1
        before = len(errors)
        found = []
        check_variant(doc, lib.resolve(doc, answers), questions, rbac, data_plane, found.append)
        for f in found:
            message = f"{rel}: [{describe(answers)}] {f}"
            if message not in errors:
                errors.append(message)
        if len(errors) - before > 12:
            errors.append(f"{rel}: ... further variants not listed")
            break
    return errors, count


def main():
    ap = argparse.ArgumentParser(description='Validate patterns against the pattern format.')
    ap.add_argument('patterns', nargs='*', help='pattern ids, directories or pattern.yaml files; default: every pattern')
    args = ap.parse_args()

    try:
        import yaml
    except ImportError:
        bad('no YAML parser available')
        say('       Install one and re-run:', 'gray')
        say('         pip install pyyaml', 'gray')
        return 2

    targets = args.patterns or lib.pattern_ids()
    if not targets:
        bad('no patterns found under patterns/')
        return 2
    questions = check_spec.load_question_index(yaml)
    kinds = spec_ref.load_kinds(yaml)
    rbac, data_plane = lib.load_roles(yaml)

    say(f"Pattern check - {len(targets)} pattern(s)", 'cyan')
    print('-' * 70)
    errors = []
    for t in targets:
        path = lib.path_of(t)
        if not path:
            bad(f"no pattern at {t}")
            return 2
        try:
            with open(path, encoding='utf-8') as f:
                doc = yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"{t}: YAML does not parse: {e}")
            bad(t)
            continue
        e, count = check_pattern(path, doc, questions, kinds, rbac, data_plane)
        errors.extend(e)
        name = doc.get('id') if isinstance(doc, dict) else t
        (bad if e else ok)(f"{name} - {len((doc or {}).get('parts') or {})} part(s), {count} variant(s)"
                           + (f", {len(e)} problem(s)" if e else ''))

    print('-' * 70)
    if errors:
        print()
        bad(f"{len(errors)} violation(s)")
        for e in errors:
            say(f"         {e}", 'gray')
        return 1
    print()
    say(f"{len(targets)} pattern(s) match the format in every variant.", 'green')
    return 0


if __name__ == '__main__':
    sys.exit(main())
