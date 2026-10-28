#!/usr/bin/env python3
"""Prints what an interview needs from the question sets, without the reasoning around it.

Read-only. The deployment set alone is over 2,000 lines, and a run that reads it in full
spends most of its context on `why` texts it never quotes. A run that extracts the
interview questions with an ad-hoc script loses the rules that decide whether they are asked
- `forced_when` above all, which is prose and the reason a question is skipped. This digest
is the one shortcut that keeps them. For the deployment set (always) and every set given:

  1. Interview questions (`resolved_by: interview`), by topic: id, type, ask, the values
     with their customer wording in the chosen language, default, required, depends_on
     and `forced_when` in full.
  2. Every other question a run must act on: `forced_when`, `derived_from`,
     `non_production_default` or `required` - one entry each, never asked, but each one a
     consequence to apply, an open item or a Phase 4 row.
  3. A resource set's boundaries: what it does not create, said out loud rather than
     improvised.

A question with `accepts: { catalogue: ... }` also prints the newest generally available entries of
that catalogue (the Foundry models), so the options come from it and not from memory.

`why` is left out; `--why <id>` prints it for the questions named, when a default must be
justified or an answer read against its reasoning.

Needs PyYAML (pip install pyyaml). Without it the script says so and exits 2.

Usage:
    python3 interview_digest.py [<set>...] [--language de] [--why <id> ...]

A set is a questions.yaml, a resource directory, or `<family>/<resource>` under resources/
(`compute/app-service`). Exit 0 printed, 2 could not read a set.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
DEPLOYMENT_SET = os.path.abspath(os.path.join(HERE, '..', 'questions', 'deployment.yaml'))
RESOURCES = os.path.join(PLUGIN, 'resources')
TOPICS = ['platform', 'network', 'security', 'resilience', 'data', 'application']
ACTED_ON = ['forced_when', 'derived_from', 'non_production_default', 'required']


def resolve(arg):
    """A set argument to its questions.yaml, or None."""
    for p in (arg, os.path.join(RESOURCES, arg)):
        if os.path.isfile(p):
            return os.path.abspath(p)
        q = os.path.join(p, 'questions.yaml')
        if os.path.isfile(q):
            return os.path.abspath(q)
    return None


def questions_of(doc):
    for g in doc.get('groups') or []:
        for q in g.get('questions') or []:
            yield g.get('id'), q


def flat(text):
    return ' '.join(str(text).split())


def wording(entry, language):
    if isinstance(entry, dict):
        return entry.get(language) or entry.get('en') or ''
    return str(entry)


def values_line(q, language):
    labels = q.get('plain_values') or {}
    accepts = q.get('accepts')
    if isinstance(accepts, list):
        return '; '.join(
            f"{v} = {flat(wording(labels.get(v, labels.get(str(v), '')), language))}".rstrip(' =')
            for v in accepts)
    if isinstance(accepts, dict) and accepts.get('ref'):
        return f"a reference to a {accepts['ref']}"
    if q.get('offer'):
        return '; '.join(f"{k} = {flat(wording(v, language))}" for k, v in q['offer'].items())
    return ''


def catalogue_lines(set_path, q, per_family=6):
    """An `accepts` catalogue as the interview offers it: per kind, one line per
    family (the catalogue's `format`, most models first) with the deployment types it
    comes in, then its newest generally available models, one version each."""
    import yaml
    name = q['accepts']['catalogue']
    src = os.path.join(PLUGIN, os.path.dirname(set_path), str(name))
    try:
        with open(src, encoding='utf-8') as f:
            cat = yaml.safe_load(f) or {}
    except OSError:
        return [f"   catalogue: {name} - missing; offer no model, the question stays open"]
    lines = [f"   catalogue: {name} (retrieved {cat.get('retrieved')}) - offer only these, never one from memory"]
    families = {}
    for m in cat.get('models') or []:
        if m.get('lifecycle') != 'GenerallyAvailable':
            continue
        fam = families.setdefault((m.get('kind'), m.get('format')), {'types': set(), 'models': {}})
        fam['types'].update(m.get('deployment_types') or {})
        fam['models'].setdefault(m.get('name'), m)
    for kind in sorted({k for k, _ in families}):
        ranked = sorted(((f, v) for (k, f), v in families.items() if k == kind),
                        key=lambda fv: (-len(fv[1]['models']), str(fv[0])))
        for fmt, fam in ranked:
            lines.append(f"     {kind} {fmt} [{','.join(sorted(fam['types']))}]")
            for m in list(fam['models'].values())[:per_family]:
                types = ','.join(m.get('deployment_types') or {})
                lines.append(f"       {m.get('name')} {m.get('version')} {types}")
    return lines


def condition(dep):
    if not isinstance(dep, dict):
        return str(dep)
    for op in ('equals', 'not_equals', 'contains'):
        if op in dep:
            return f"{dep.get('question')} {op} {dep[op]}"
    return str(dep)


def digest(name, doc, language, why_ids, out):
    out.append(f"== {name}")
    interview = [(g, q) for g, q in questions_of(doc) if q.get('resolved_by') == 'interview']
    acted = [(g, q) for g, q in questions_of(doc)
             if q.get('resolved_by') != 'interview' and any(k in q for k in ACTED_ON)]

    if interview:
        out.append('-- interview (put to the customer, unless forced_when settles it)')
        order = {t: i for i, t in enumerate(TOPICS)}
        for g, q in sorted(interview, key=lambda gq: order.get(gq[1].get('topic'), len(TOPICS))):
            head = f"[{q.get('topic')}] {q['id']}  {q.get('type')}"
            if 'default' in q:
                head += f"  default={q['default']}"
            if q.get('required'):
                head += '  required'
            out.append(head)
            out.append(f"   ask: {flat(wording(q.get('ask', ''), language))}")
            vals = values_line(q, language)
            if vals:
                out.append(f"   values: {vals}")
            if q.get('depends_on'):
                out.append(f"   only if: {condition(q['depends_on'])}")
            if q.get('forced_when'):
                out.append(f"   forced_when: {flat(q['forced_when'])}")
            if isinstance(q.get('accepts'), dict) and q['accepts'].get('catalogue'):
                out.extend(catalogue_lines(name, q))
            if q['id'] in why_ids:
                out.append(f"   why: {flat(q.get('why', ''))}")

    if acted:
        out.append('-- not asked, but acted on (consequences, open items, Phase 4 rows)')
        for g, q in acted:
            parts = [f"{g}.{q['id']}"]
            if q.get('required'):
                parts.append('required (unanswered: an open item with its owner)')
            if q.get('derived_from'):
                d = q['derived_from']
                parts.append(f"derived_from {d.get('question')} {d.get('map')}")
            if 'non_production_default' in q:
                parts.append(f"non_production_default={q['non_production_default']}")
            if q.get('depends_on'):
                parts.append(f"only if {condition(q['depends_on'])}")
            out.append('  ' + '  '.join(parts))
            if q.get('forced_when'):
                out.append(f"   forced_when: {flat(q['forced_when'])}")
            if isinstance(q.get('accepts'), dict) and q['accepts'].get('catalogue'):
                out.extend(catalogue_lines(name, q))
            if q['id'] in why_ids:
                out.append(f"   why: {flat(q.get('why', ''))}")

    others = [q for _, q in questions_of(doc)
              if q['id'] in why_ids and q.get('resolved_by') != 'interview'
              and not any(k in q for k in ACTED_ON)]
    for q in others:
        out.append(f"  {q['id']}  why: {flat(q.get('why', ''))}")

    if doc.get('boundaries'):
        out.append('-- boundaries (not created by this set; say so, never improvise)')
        for b in doc['boundaries']:
            out.append(f"  - {flat(b)}")
    out.append('')


def main():
    ap = argparse.ArgumentParser(description='Print the interview digest of the deployment set and the sets given.')
    ap.add_argument('sets', nargs='*', help='questions.yaml, a resource directory, or <family>/<resource>')
    ap.add_argument('--language', default='en', help='customer wording of the values: en (default) or de')
    ap.add_argument('--why', nargs='*', default=[], metavar='ID', help='also print the why of these questions')
    args = ap.parse_args()

    try:
        import yaml
    except ImportError:
        print('[fail] no YAML parser available - pip install pyyaml', file=sys.stderr)
        return 2
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    paths = [DEPLOYMENT_SET]
    for s in args.sets:
        p = resolve(s)
        if not p:
            print(f"[fail] no question set at {s}", file=sys.stderr)
            return 2
        if p not in paths:
            paths.append(p)

    out = []
    for p in paths:
        with open(p, encoding='utf-8') as f:
            doc = yaml.safe_load(f)
        name = os.path.relpath(p, PLUGIN).replace(os.sep, '/')
        digest(name, doc, args.language, set(args.why), out)
    print('\n'.join(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
