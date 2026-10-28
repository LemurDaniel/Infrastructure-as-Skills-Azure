#!/usr/bin/env python3
"""Validates question sets against the question-set format.

Read-only. The repo's check_repo_consistency.py reads the files with regexes
and catches the structural mistakes; this script parses them and checks what
a regex cannot see - what references/question-set-format.md promises:

  1. The envelope: schema_version, scope, title; for a resource set the
     resource type and both naming identifiers plus the abbreviation, the
     Bicep identifier without `Azure::`, the Terraform one with it, and the
     two agreeing.
  2. Groups: unique ids, each with a title and questions, the review-order
     groups (placement, networking, identity, security, data_protection,
     observability) in that relative order.
  3. Questions: unique ids; id, ask, type, why and renders present; a known
     type; `accepts` - a list of values (required on an enum, optional on a
     list) or `{ ref: <kind> }` (on a string or a list); a default within the
     accepted values (enum) or a subset of them (list); a default of the type's kind.
  4. Resolution: `required`, `default`, `answer` and `parameterized` are
     mutually exclusive, and a question carries one of them - a question with
     none has no answer path. `answer` is `{ deployment: <id> }`,
     `{ context: <id> }` or `{ question: <id>, map: {...} }`.
  5. References: `depends_on` names a question in the same set and, for an
     enum, a value it can take; `answer.deployment` and `answer.context` name a
     question in the deployment set (its context group for the latter); `answer.question` names an interview question in the
     deployment set and maps every one of its values to a value of this
     question's kind (and, for an enum, one of its values).
  6. `resolved_by`, where present, is interview or derived; absent means the question
     is defaulted or derived and never asked. An interview question carries a `topic`
     (platform, network, security, resilience, data, application) and no other does.
     A question that inherits its answer (answer.deployment, answer.context) is never interview, and
     is derived exactly where the deployment question it inherits from is.
  7. `ask` and `plain` are mappings of language code to one line (`en`
     required; `{value}` optional in `plain`), and `plain_values`, where
     present, maps every key to such a mapping and names only values the
     question can take - the decision document reads both.
  8. Stages: `per_environment` is a bool, and a question inheriting a
     per-stage deployment question through `answer.deployment` is per-stage
     too; `non_production_default` is of the question's kind, within its
     values, and never in a security, networking, identity, access, DNS,
     compliance or posture group - a cheaper stage is never a less secure one.
  9. Unknown fields are reported: a misspelt `default` is a question that is
     silently asked every run.

Needs PyYAML (pip install pyyaml). Without it the script says so and exits 2
rather than pretending the files are fine.

Usage:
    python3 check_question_set.py <path>...

A path is a questions.yaml, a resource directory, a family directory, the
resources root, or the deployment set. Directories are searched for
questions.yaml and questions/*.yaml. With no path, every set in the plugin.

Exit 0 clean, 1 violations, 2 could not check (no parser, no file).
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
DEPLOYMENT_SET = os.path.join(HERE, '..', 'questions', 'deployment.yaml')

TYPES = ['enum', 'bool', 'string', 'int', 'list']
RESOLVED_BY = ['interview', 'derived']
TOPICS = ['platform', 'network', 'security', 'resilience', 'data', 'application']
REVIEW_ORDER = ['placement', 'networking', 'identity', 'security', 'data_protection', 'observability']
RESOLUTION_FIELDS = ['required', 'default', 'answer', 'parameterized']
KNOWN_FIELDS = {
    'id', 'ask', 'type', 'accepts', 'default', 'required', 'parameterized',
    'why', 'renders', 'depends_on', 'answer', 'forced_when',
    'resolved_by', 'topic', 'plain', 'plain_values', 'per_environment', 'non_production_default',
    'offer',
}
# Groups whose decisions may never be relaxed for a non-production stage.
NO_SAVINGS_GROUPS = {'security', 'networking', 'identity', 'access', 'dns', 'compliance', 'posture', 'modules', 'subnet_policy'}
DERIVED_KEYS = {'question', 'map'}
ANSWER_FORMS = ({'deployment'}, {'context'}, DERIVED_KEYS)
KNOWN_TOP = {'schema_version', 'scope', 'resource', 'title', 'naming', 'boundaries', 'groups'}

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


def find_sets(paths):
    """Expand files and directories into question-set paths, sorted, unique."""
    found = set()
    for p in paths:
        if os.path.isfile(p):
            found.add(os.path.abspath(p))
            continue
        if not os.path.isdir(p):
            bad(f"no such file or directory: {p}")
            continue
        for d, dirs, files in os.walk(p):
            dirs[:] = [x for x in dirs if x not in ('.git', 'node_modules', '.terraform', 'results')]
            for f in files:
                full = os.path.join(d, f)
                if re.match(r'^questions\.ya?ml$', f) or (
                        os.path.basename(d) == 'questions' and re.search(r'\.ya?ml$', f)):
                    found.add(os.path.abspath(full))
    return sorted(found)


def questions_of(doc):
    """Every question in a parsed set, with its group id."""
    out = []
    for g in (doc.get('groups') or []) if isinstance(doc, dict) else []:
        if not isinstance(g, dict):
            continue
        for q in (g.get('questions') or []):
            if isinstance(q, dict):
                out.append((g.get('id'), q))
    return out


def accepted(q):
    """The values a question accepts, or None for a free value or a reference."""
    a = q.get('accepts')
    return a if isinstance(a, list) else None


ACCEPTS_FORMS = ({'ref'}, {'catalogue'})


def kind_matches(qtype, value):
    if qtype == 'bool':
        return isinstance(value, bool)
    if qtype == 'int':
        return isinstance(value, int) and not isinstance(value, bool)
    if qtype == 'string':
        return isinstance(value, str)
    if qtype == 'enum':
        return isinstance(value, (str, int, bool))
    if qtype == 'list':
        return isinstance(value, list)
    return True


def check_set(path, doc, deployment, rel):
    """Returns (errors, warnings, question count)."""
    errors, warnings = [], []

    def err(t): errors.append(f"{rel}: {t}")
    def wrn(t): warnings.append(f"{rel}: {t}")

    if not isinstance(doc, dict):
        err('does not parse as a mapping')
        return errors, warnings, 0

    # --- 1. envelope -------------------------------------------------------
    scope = doc.get('scope', 'resource')
    if scope not in ('resource', 'deployment'):
        err(f"scope '{scope}' is not resource or deployment")
    if 'schema_version' not in doc:
        err('schema_version is missing')
    if not doc.get('title'):
        err('title is missing')
    for k in doc:
        if k not in KNOWN_TOP:
            wrn(f"unknown top-level field '{k}'")

    if scope == 'resource':
        if not doc.get('resource'):
            err('resource (the Azure resource type) is missing')
        naming = doc.get('naming')
        if not isinstance(naming, dict):
            err('naming block is missing - both identifiers and the abbreviation are declared here')
        else:
            tf, bc, ab = naming.get('terraform'), naming.get('bicep'), naming.get('abbreviation')
            if not tf:
                err('naming.terraform is missing')
            elif not str(tf).startswith('Azure::'):
                err(f"naming.terraform '{tf}' lacks the Azure:: prefix the naming provider expects")
            if not bc:
                err('naming.bicep is missing')
            elif str(bc).startswith('Azure::'):
                err(f"naming.bicep '{bc}' carries an Azure:: prefix; Bicep spells the type bare")
            if tf and bc and str(tf) != f"Azure::{bc}":
                err(f"naming.terraform '{tf}' and naming.bicep '{bc}' name different types")
            if not ab:
                err('naming.abbreviation is missing - the Bicep render assembles the name from it')
            elif not re.match(r'^[a-z0-9]{1,8}$', str(ab)):
                err(f"naming.abbreviation '{ab}' is not short lowercase alphanumeric")
            if bc and doc.get('resource') and str(bc) != str(doc['resource']):
                wrn(f"naming.bicep '{bc}' differs from resource '{doc['resource']}'")
    else:
        for k in ('resource', 'naming'):
            if k in doc:
                err(f"a deployment set names no resource; drop '{k}'")

    # --- 2. groups ---------------------------------------------------------
    groups = doc.get('groups')
    if not isinstance(groups, list) or not groups:
        err('groups is missing or empty')
        return errors, warnings, 0
    gids = []
    for g in groups:
        if not isinstance(g, dict):
            err('a group is not a mapping')
            continue
        gid = g.get('id')
        if not gid:
            err('a group has no id')
        gids.append(gid)
        if not g.get('title'):
            err(f"group '{gid}' has no title")
        if not isinstance(g.get('questions'), list) or not g['questions']:
            err(f"group '{gid}' has no questions")
    dupes = sorted({x for x in gids if gids.count(x) > 1}, key=str)
    if dupes:
        err(f"duplicate group id(s): {', '.join(map(str, dupes))}")
    if scope == 'resource':
        seen = [g for g in gids if g in REVIEW_ORDER]
        if seen != sorted(seen, key=REVIEW_ORDER.index):
            wrn(f"review-order groups out of order: {' -> '.join(seen)}; the format fixes "
                f"{' -> '.join(REVIEW_ORDER)} so a reviewer does not relearn the layout per resource")

    # --- 3-7. questions ----------------------------------------------------
    qs = questions_of(doc)
    ids = [q.get('id') for _, q in qs]
    dupes = sorted({x for x in ids if ids.count(x) > 1}, key=str)
    if dupes:
        err(f"duplicate question id(s): {', '.join(map(str, dupes))}. Ids are an interface - pattern pre-answers and specs name them.")
    by_id = {q.get('id'): q for _, q in qs}

    dep_ids = {q.get('id'): q for _, q in questions_of(deployment)} if deployment else {}
    dep_context = {q.get('id') for g, q in questions_of(deployment) if g == 'context'} if deployment else set()

    for gid, q in qs:
        qid = q.get('id') or '<no id>'
        where = f"{gid}.{qid}"

        for k in q:
            if k not in KNOWN_FIELDS:
                err(f"{where}: unknown field '{k}'" + (" - did you mean 'default'?" if k.lower().startswith('def') else ''))

        for k in ('id', 'ask', 'type', 'why', 'renders'):
            if not q.get(k):
                err(f"{where}: '{k}' is missing")
        if q.get('why') and len(str(q['why']).strip()) < 40:
            wrn(f"{where}: why is one line; the format wants what breaks or what it costs if the other value is chosen")

        qtype = q.get('type')
        if qtype and qtype not in TYPES:
            err(f"{where}: type '{qtype}' is not one of {', '.join(TYPES)}")

        acc = q.get('accepts')
        values = accepted(q)
        if acc is not None and not (isinstance(acc, list) and acc) and not (
                isinstance(acc, dict) and set(acc) in ACCEPTS_FORMS and all(isinstance(v, str) and v for v in acc.values())):
            err(f"{where}: accepts must be a non-empty list of values, {{ ref: <kind> }} or {{ catalogue: <file> }}")
        elif qtype == 'enum' and values is None:
            err(f"{where}: an enum needs accepts: [<value>, ...]")
        elif isinstance(acc, dict) and qtype not in ('string', 'list'):
            err(f"{where}: accepts: {{ {next(iter(acc))}: ... }} on a {qtype} question; it takes a string or a list")
        elif values is not None and qtype not in ('enum', 'list'):
            wrn(f"{where}: accepts on a {qtype} question is not read; only enum and list take a value list")
        if values is not None:
            vd = sorted({str(v) for v in values if values.count(v) > 1})
            if vd:
                err(f"{where}: duplicate value(s): {', '.join(vd)}")

        # --- 4. resolution: one answer path; `answer` names where an inherited one comes from
        ans = q.get('answer')
        fd = ctx = dv = None
        if ans is not None:
            if not isinstance(ans, dict) or set(ans) not in ANSWER_FORMS:
                err(f"{where}: answer must be {{ deployment: <id> }}, {{ context: <id> }} or {{ question: <id>, map: {{...}} }}")
            else:
                fd, ctx = ans.get('deployment'), ans.get('context')
                dv = ans if 'question' in ans else None
        # `default: false` is a default; `required: false` is not a requirement.
        present = [f for f in RESOLUTION_FIELDS if q.get(f) is not None
                   and not (f in ('required', 'parameterized') and q[f] is False)]
        if len(present) > 1:
            err(f"{where}: {' and '.join(present)} together; they are mutually exclusive")
        if not present:
            err(f"{where}: no required, default, answer or parameterized - the question has no answer path")
        if 'required' in q and not isinstance(q['required'], bool):
            err(f"{where}: required must be true or false")
        if 'parameterized' in q and not isinstance(q['parameterized'], bool):
            err(f"{where}: parameterized must be true or false")
        if q.get('parameterized') and scope != 'deployment':
            wrn(f"{where}: parameterized outside the deployment set; context values live there")

        if 'default' in q and q['default'] is not None and qtype:
            d = q['default']
            if not kind_matches(qtype, d):
                err(f"{where}: default {d!r} is not a {qtype}")
            if qtype == 'enum' and isinstance(values, list) and d not in values:
                err(f"{where}: default '{d}' is not in accepts {values}")
            if qtype == 'list' and isinstance(values, list) and isinstance(d, list):
                off = [x for x in d if x not in values]
                if off:
                    err(f"{where}: default item(s) not in accepts: {off}")

        # --- 5. references
        dep = q.get('depends_on')
        if dep is not None:
            if not isinstance(dep, dict) or 'question' not in dep:
                err(f"{where}: depends_on must be {{ question: <id>, equals: <value> }} or not_equals")
            else:
                target = dep['question']
                cond = [k for k in ('equals', 'not_equals', 'contains') if k in dep]
                if len(cond) != 1:
                    err(f"{where}: depends_on needs exactly one of equals / not_equals / contains")
                extra = set(dep) - {'question', 'equals', 'not_equals', 'contains'}
                if extra:
                    err(f"{where}: depends_on has unknown key(s) {sorted(extra)}")
                if target == qid:
                    err(f"{where}: depends_on itself")
                elif target not in by_id:
                    err(f"{where}: depends_on '{target}', which is not a question in this set")
                elif cond:
                    tq = by_id[target]
                    tv = accepted(tq)
                    v = dep[cond[0]]
                    if cond[0] == 'contains' and tq.get('type') != 'list':
                        err(f"{where}: depends_on contains needs a list question, but {target} is {tq.get('type')}")
                    if tq.get('type') == 'enum' and isinstance(tv, list) and v not in tv:
                        err(f"{where}: depends_on {target} {cond[0]} '{v}', which {target} cannot take (accepts {tv})")
                    if cond[0] == 'contains' and isinstance(tv, list) and v not in tv:
                        err(f"{where}: depends_on {target} contains '{v}', which {target} cannot hold (accepts {tv})")
                    if tq.get('type') == 'bool' and not isinstance(v, bool):
                        err(f"{where}: depends_on {target} {cond[0]} {v!r}, but {target} is a bool")

        if fd is not None:
            if scope == 'deployment':
                err(f"{where}: answer.deployment inside the deployment set")
            elif deployment is None:
                wrn(f"{where}: answer.deployment '{fd}' not checked - the deployment set did not load")
            elif fd not in dep_ids:
                err(f"{where}: answer.deployment '{fd}', which the deployment set does not have")
            else:
                tq = dep_ids[fd]
                if qtype == 'enum' and tq.get('type') == 'enum' and isinstance(values, list):
                    tv = accepted(tq) or []
                    if set(map(str, tv)) == set(map(str, values)):
                        pass  # same vocabulary, inherited as-is
                    # different vocabularies are mapped in `why`; nothing to check mechanically

        if dv is not None:
            if scope == 'deployment':
                err(f"{where}: answer.question inside the deployment set")
            elif deployment is None:
                wrn(f"{where}: answer.question '{dv.get('question')}' not checked - the deployment set did not load")
            elif dv['question'] not in dep_ids:
                err(f"{where}: answer.question '{dv['question']}', which the deployment set does not have")
            else:
                tq = dep_ids[dv['question']]
                if tq.get('resolved_by') != 'interview':
                    err(f"{where}: answer.question '{dv['question']}', which the interview does not ask - a derivation answers an interview question; otherwise use answer.deployment")
                tv = accepted(tq) if tq.get('type') == 'enum' else None
                m = dv['map']
                if not isinstance(m, dict) or not m:
                    err(f"{where}: answer.map must be a non-empty mapping")
                else:
                    if tv is not None:
                        missing = [v for v in tv if v not in m]
                        extra = [k for k in m if k not in tv]
                        if missing:
                            err(f"{where}: answer.map has no entry for {missing} - every answer to {dv['question']} must derive a value")
                        if extra:
                            err(f"{where}: answer.map names answer(s) {extra} that {dv['question']} cannot take")
                    for k, v in m.items():
                        if qtype and not kind_matches(qtype, v):
                            err(f"{where}: answer.map[{k!r}] = {v!r} is not a {qtype}")
                        if qtype == 'enum' and isinstance(values, list) and v not in values:
                            err(f"{where}: answer.map[{k!r}] = '{v}' is not in accepts {values}")

        if ctx is not None:
            if scope == 'deployment':
                err(f"{where}: answer.context inside the deployment set")
            elif deployment is not None and ctx not in dep_context:
                err(f"{where}: answer.context '{ctx}', which the deployment set's context group does not have")

        # --- 8. stages
        pe = q.get('per_environment')
        if pe is not None and not isinstance(pe, bool):
            err(f"{where}: per_environment must be true or false")
        if fd is not None and deployment is not None and fd in dep_ids:
            if dep_ids[fd].get('per_environment') and not pe:
                err(f"{where}: inherits '{fd}', which is per_environment, so it is per-stage too - mark it")
            if pe and not dep_ids[fd].get('per_environment'):
                wrn(f"{where}: per_environment, but the inherited '{fd}' is not - one value for all stages there")
        npd = q.get('non_production_default')
        if npd is not None:
            if gid in NO_SAVINGS_GROUPS:
                err(f"{where}: non_production_default in group '{gid}' - a non-production stage is never less secure, exposed or differently governed than production")
            if qtype and not kind_matches(qtype, npd):
                err(f"{where}: non_production_default {npd!r} is not a {qtype}")
            if qtype == 'enum' and isinstance(values, list) and npd not in values:
                err(f"{where}: non_production_default '{npd}' is not in accepts {values}")
            if pe:
                err(f"{where}: non_production_default on a per_environment question - the stage file carries the value, not a default")

        # --- 7. ask and plain: one line per language, en required
        for field in ('ask', 'plain'):
            pl = q.get(field)
            if pl is None:
                if field == 'plain':
                    err(f"{where}: plain is missing - the one customer-language line the decision document reads")
            elif not isinstance(pl, dict) or not isinstance(pl.get('en'), str) or not pl['en'].strip():
                err(f"{where}: {field} must be a mapping with at least en: <one line>")
            else:
                for lang, text in pl.items():
                    if not re.match(r'^[a-z]{2}$', str(lang)):
                        err(f"{where}: {field}.{lang} is not a two-letter language code")
                    elif not isinstance(text, str) or '\n' in text.strip():
                        err(f"{where}: {field}.{lang} must be one line")
        offer = q.get('offer')
        if offer is not None:
            if qtype == 'enum':
                err(f"{where}: offer on an enum - its values are what the interview offers")
            elif not isinstance(offer, dict) or not offer:
                err(f"{where}: offer must be a mapping of option -> {{ en: ..., de: ... }}, the options the interview puts to the person")
            else:
                if q.get('resolved_by') != 'interview':
                    wrn(f"{where}: offer on a question that is not asked; only resolved_by: interview reaches a person")
                off = [o for o in offer if not kind_matches('list' if qtype == 'list' else qtype, [o] if qtype == 'list' else o)]
                if off:
                    err(f"{where}: offer option(s) {off} are not a {qtype}")
                if any(not isinstance(v, dict) or not isinstance(v.get('en'), str) for v in offer.values()):
                    err(f"{where}: every offer option needs a label mapping with at least en")
                room = 3 if qtype == 'list' else 4   # a list keeps one option for the explicit empty answer
                if len(offer) > room:
                    err(f"{where}: offer holds {len(offer)} options; a question shows four"
                        + (", and one of them is the empty answer" if qtype == 'list' else ''))
        src = acc.get('catalogue') if isinstance(acc, dict) else None
        if src is not None:
            full = os.path.join(os.path.dirname(path), str(src))
            if not os.path.isfile(full):
                err(f"{where}: accepts catalogue '{src}' does not exist beside the set")
            else:
                try:
                    import yaml
                    with open(full, encoding='utf-8') as f:
                        cat = yaml.safe_load(f)
                except Exception as e:
                    cat = None
                    err(f"{where}: accepts catalogue '{src}' does not parse: {e}")
                if cat is not None and (not isinstance(cat, dict) or not cat.get('retrieved')
                                        or not isinstance(cat.get('models'), list) or not cat['models']):
                    err(f"{where}: accepts catalogue '{src}' needs retrieved: <date> and a non-empty models list")
        pv = q.get('plain_values')
        if pv is not None:
            if not isinstance(pv, dict) or not pv:
                err(f"{where}: plain_values must be a non-empty mapping of value -> {{ en: ..., ... }}")
            else:
                allowed = values if isinstance(values, list) else ([True, False] if qtype == 'bool' else (list(offer) if isinstance(offer, dict) else None))
                for k, v in pv.items():
                    if allowed is not None and k not in allowed:
                        err(f"{where}: plain_values names '{k}', which the question cannot take")
                    if not isinstance(v, dict) or not isinstance(v.get('en'), str):
                        err(f"{where}: plain_values[{k!r}] must be a mapping with at least en")
                if pl and '{value}' not in pl.get('en', ''):
                    wrn(f"{where}: plain_values given but plain.en has no {{value}} placeholder")

        # --- 6. resolved_by (absent: defaulted or derived, never asked)
        rb = q.get('resolved_by')
        if rb is not None and rb not in RESOLVED_BY:
            err(f"{where}: resolved_by '{rb}' is not one of {', '.join(RESOLVED_BY)}")
        # a question that inherits its answer is never asked again; it repeats `derived` from its source
        if (fd is not None or ctx is not None) and rb == 'interview':
            err(f"{where}: a question that inherits its answer (answer.deployment, answer.context) "
                f"is never `interview` - the deployment set asks it once")
        if fd is not None and deployment is not None and fd in dep_ids:
            src = dep_ids[fd].get('resolved_by')
            if src == 'derived' and rb != 'derived':
                err(f"{where}: answer.deployment '{fd}' is `derived`, so this one is too - "
                    f"an open value goes to the platform team")
            elif src != 'derived' and rb == 'derived':
                err(f"{where}: `derived`, but answer.deployment '{fd}' is not")
        # --- 6b. topic: the heading an interview question stands under in the batch
        tp = q.get('topic')
        if rb == 'interview' and tp is None:
            err(f"{where}: an interview question needs a `topic` ({', '.join(TOPICS)})")
        elif tp is not None and rb != 'interview':
            err(f"{where}: `topic` belongs to interview questions only; this one is not asked")
        elif tp is not None and tp not in TOPICS:
            err(f"{where}: topic '{tp}' is not one of {', '.join(TOPICS)}")

    return errors, warnings, len(qs)


def main():
    ap = argparse.ArgumentParser(description='Validate question sets against the question-set format.')
    ap.add_argument('paths', nargs='*', help='questions.yaml files or directories holding them; default: the whole plugin')
    args = ap.parse_args()

    try:
        import yaml
    except ImportError:
        bad('no YAML parser available')
        say('       Install one and re-run:', 'gray')
        say('         pip install pyyaml', 'gray')
        return 2

    def load(p):
        with open(p, encoding='utf-8') as f:
            return yaml.safe_load(f)

    deployment = None
    dep_path = os.path.abspath(DEPLOYMENT_SET)
    if os.path.isfile(dep_path):
        try:
            deployment = load(dep_path)
        except yaml.YAMLError:
            deployment = None

    paths = args.paths or [PLUGIN]
    sets = find_sets(paths)
    if not sets:
        bad('no question sets found')
        return 2

    say(f"Question-set check - {len(sets)} file(s)", 'cyan')
    print('-' * 70)

    errors, warnings, total = [], [], 0
    for p in sets:
        rel = os.path.relpath(p, PLUGIN) if p.startswith(PLUGIN) else p
        try:
            doc = load(p)
        except yaml.YAMLError as e:
            errors.append(f"{rel}: YAML does not parse: {e}")
            bad(rel)
            continue
        dep = deployment if os.path.abspath(p) != dep_path else None
        e, w, n = check_set(p, doc, dep, rel)
        total += n
        errors.extend(e)
        warnings.extend(w)
        scope = doc.get('scope', 'resource') if isinstance(doc, dict) else '?'
        (bad if e else ok)(f"{rel} - {n} question(s), scope {scope}" + (f", {len(e)} problem(s)" if e else ''))

    print('-' * 70)
    for w in warnings:
        warn(w)
    if errors:
        print()
        bad(f"{len(errors)} violation(s) across {len(sets)} file(s)")
        for e in errors:
            say(f"         {e}", 'gray')
        return 1
    print()
    say(f"{total} question(s) in {len(sets)} set(s) match the format." + (f" {len(warnings)} warning(s)." if warnings else ''), 'green')
    return 0


if __name__ == '__main__':
    sys.exit(main())
