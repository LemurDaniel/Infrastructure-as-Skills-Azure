#!/usr/bin/env python3
"""Renders an infra-spec.yaml as the customer's decision document.

The spec is written for reviewers and backends. The person who asked for the
system reads neither YAML nor HCL, and still has to recognise the decisions as
theirs. This script turns every decision in the spec into one line in the
customer's language, using the `plain` and `plain_values` texts of the
question sets:

  1. What follows from your answers - the customer-audience deployment
     decisions (environment, exposure, mandates, the requirements) with the
     decisions derived from each (`source: requirement`, `derived_from`).
  2. Set by the rules - everything defaulted, inherited or forced, per
     resource, a forced value with the decision that forced it.
  3. Decided differently by you - `overridden` values with their reason.
  4. Still open - the `open:` entries with their owner, and `assumed` values.
  5. Appendix - every decision with its key, value and source, for the
     engineer reading beside the customer.

Fixed labels come in `en` and `de`; the per-decision lines come from the
question sets, which carry `en` and may carry others. A line missing in the
requested language falls back to English and is marked, and the script says
how many fell back.

Needs PyYAML. Reads the question sets from the plugin this script ships in.

Usage:
    python3 export_decisions.py ./infra-spec.yaml [--language de] [--out ./infra-decisions.md]

The language is `context.language` of the spec; --language overrides it.

Exit 0 written, 1 the spec or a question set could not be read, 2 could not run.
"""

import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
DEPLOYMENT_SET = os.path.join(HERE, '..', 'questions', 'deployment.yaml')
RESOURCES = os.path.join(PLUGIN, 'resources')

LABELS = {
    'en': {
        'title': 'Decisions for "{workload}"',
        'intro': 'What will be built, decided from your answers and the rules behind the defaults. '
                 'Every line is one decision; the key in the appendix is where an engineer finds it in the specification.',
        'as_of': 'As of {date}. Specification: `{spec}`.',
        'context': 'The system', 'stages': 'What differs between the stages',
        'stages_intro': 'One code base is deployed through these stages; everything not listed here is identical in every stage.',
        'stage_file': 'in stage', 'savings': 'cheaper outside production',
        'answers': 'What follows from your answers',
        'answered': 'your answer', 'stated': 'from your description', 'assumed_default': 'not said, so the usual answer applies',
        'carried': 'as decided earlier',
        'derived': 'therefore', 'rules': 'Set by the rules',
        'rules_intro': 'Nothing here was asked; each follows a rule or one of the answers above. Say so if one is wrong.',
        'whole_system': 'For the whole system', 'because': 'because',
        'overridden': 'Decided differently by you', 'reason': 'reason',
        'open': 'Still open', 'open_intro': 'Nothing can be deployed until these are answered.',
        'owner': 'needed from', 'blocks': 'blocks', 'assumed': 'Placeholders',
        'assumed_intro': 'Values the run chose to keep going. They are not decisions yet.',
        'appendix': 'Appendix: every decision', 'key': 'Key', 'value': 'Value', 'source': 'Source',
        'none': 'none', 'nobody': 'nobody yet', 'yes': 'yes', 'no': 'no', 'fallback': '(en)',
        'sources': {'stated': 'your description', 'asked': 'your answer', 'platform': 'the platform profile',
                    'pattern': 'the pattern', 'requirement': 'derived from your answer', 'deployment': 'inherited',
                    'forced': 'forced', 'assumed': 'placeholder', 'default': 'rule', 'carried': 'carried',
                    'overridden': 'your departure'},
    },
    'de': {
        'title': 'Entscheidungen für „{workload}“',
        'intro': 'Was gebaut wird, entschieden aus euren Antworten und den Regeln hinter den Vorgaben. '
                 'Jede Zeile ist eine Entscheidung; der Schlüssel im Anhang ist, wo ein Engineer sie in der Spezifikation findet.',
        'as_of': 'Stand {date}. Spezifikation: `{spec}`.',
        'context': 'Das System', 'stages': 'Was sich zwischen den Stufen unterscheidet',
        'stages_intro': 'Ein Code wird durch diese Stufen ausgerollt; alles, was hier nicht steht, ist in jeder Stufe gleich.',
        'stage_file': 'in Stufe', 'savings': 'außerhalb der Produktion günstiger',
        'answers': 'Was aus euren Antworten folgt',
        'answered': 'eure Antwort', 'stated': 'aus eurer Beschreibung', 'assumed_default': 'nicht gesagt, daher gilt die übliche Antwort',
        'carried': 'wie früher entschieden',
        'derived': 'daher', 'rules': 'Nach den Vorgaben gesetzt',
        'rules_intro': 'Nichts davon wurde gefragt; jede Zeile folgt einer Regel oder einer der Antworten oben. Sagt Bescheid, wenn eine nicht passt.',
        'whole_system': 'Für das ganze System', 'because': 'weil',
        'overridden': 'Von euch anders entschieden', 'reason': 'Grund',
        'open': 'Noch offen', 'open_intro': 'Solange diese Punkte offen sind, wird nichts ausgerollt.',
        'owner': 'gebraucht von', 'blocks': 'blockiert', 'assumed': 'Platzhalter',
        'assumed_intro': 'Werte, die der Lauf angenommen hat, um weiterzukommen. Das sind noch keine Entscheidungen.',
        'appendix': 'Anhang: alle Entscheidungen', 'key': 'Schlüssel', 'value': 'Wert', 'source': 'Quelle',
        'none': 'keine', 'nobody': 'noch niemand', 'yes': 'ja', 'no': 'nein', 'fallback': '(en)',
        'sources': {'stated': 'eure Beschreibung', 'asked': 'eure Antwort', 'platform': 'das Plattformprofil',
                    'pattern': 'das Muster', 'requirement': 'abgeleitet aus eurer Antwort', 'deployment': 'übernommen',
                    'forced': 'erzwungen', 'assumed': 'Platzhalter', 'default': 'Regel', 'carried': 'übernommen',
                    'overridden': 'eure Abweichung'},
    },
}

CUSTOMER_ANSWER_SOURCES = {'stated', 'asked', 'carried', 'overridden'}


def say(text):
    print(text, file=sys.stderr)


def load_yaml(path, yaml):
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def questions_of(doc):
    out = {}
    for g in (doc.get('groups') or []):
        for q in (g.get('questions') or []):
            if isinstance(q, dict) and q.get('id'):
                out[q['id']] = (g.get('id'), q)
    return out


class Renderer:
    def __init__(self, lang, labels):
        self.lang = lang
        self.L = labels
        self.fallbacks = 0
        self.environments = []
        self.env_q = None

    def words(self, mapping):
        """A { en: ..., de: ... } mapping in the requested language, else English marked."""
        if not isinstance(mapping, dict):
            return str(mapping)
        if self.lang in mapping:
            return str(mapping[self.lang])
        self.fallbacks += 1
        return f"{mapping.get('en', '')} {self.L['fallback']}"

    def is_stage_map(self, value):
        return isinstance(value, dict) and bool(value) and all(k in self.environments for k in value)

    def stage_name(self, stage):
        pv = (self.env_q or {}).get('plain_values') or {}
        return self.words(pv[stage]) if stage in pv else stage

    def value_words(self, q, value):
        pv = (q or {}).get('plain_values') or {}
        if self.is_stage_map(value):
            if len(self.environments) == 1:
                # One stage is the whole system: no stage prefix on a value that cannot differ.
                return self.value_words(q, next(iter(value.values())))
            return '; '.join(f"{self.stage_name(k)}: {self.value_words(q, v)}" for k, v in value.items())
        if isinstance(value, bool):
            if value in pv:
                return self.words(pv[value])
            return self.L['yes'] if value else self.L['no']
        if isinstance(value, list):
            if not value:
                return self.L['none']
            return ', '.join(self.value_words(q, v) for v in value)
        if isinstance(value, dict):
            # a role granted to a principal, a subnet handed to a service: pairs read as "who (what)"
            for who, what in (('principal', 'role'), ('subnet', 'service')):
                if who in value and what in value:
                    return f"{value[who]} ({value[what]})"
            if 'name' in value:
                detail = value.get('resource_group_name') or value.get('prefix')
                base = str(value['name']) + (f" ({detail})" if detail else '')
                extra = {k: v for k, v in value.items() if k not in ('name', 'resource_group_name', 'prefix', 'purpose')}
                return base + (' ' + ', '.join(f"{k} {v}" for k, v in extra.items()) if extra else '')
            return ', '.join(f"{k}: {self.value_words(None, v)}" for k, v in value.items())
        try:
            if value in pv:
                return self.words(pv[value])
        except TypeError:
            pass
        return str(value)

    def line(self, q, value):
        if not q or not isinstance(q.get('plain'), dict):
            return f"`{json.dumps(value, ensure_ascii=False)}`"
        text = self.words(q['plain'])
        return text.replace('{value}', self.value_words(q, value))


def main():
    ap = argparse.ArgumentParser(description="Render an infra-spec.yaml as the customer's decision document.")
    ap.add_argument('spec', help='the infra-spec.yaml')
    ap.add_argument('--language', help="two-letter language code (default: the spec's context.language, else en; others fall back per line)")
    ap.add_argument('--out', help='output path (default: infra-decisions.md beside the spec)')
    args = ap.parse_args()

    try:
        import yaml
    except ImportError:
        say('[fail] no YAML parser available (pip install pyyaml)')
        return 2
    if not os.path.isfile(args.spec):
        say(f"[fail] no such file: {args.spec}")
        return 2
    with open(args.spec, encoding='utf-8') as f:
        ctx_lang = ((yaml.safe_load(f) or {}).get('context') or {}).get('language')
    requested = args.language or (str(ctx_lang) if ctx_lang else None) or 'en'
    lang = requested if requested in LABELS else 'en'
    L = LABELS[lang]
    if lang != requested:
        say(f"[warn] no fixed labels for '{requested}'; using en labels, per-decision lines in '{requested}' where the sets carry them")
        lang = requested
        R = Renderer(lang, L)
    else:
        R = Renderer(lang, L)

    try:
        spec = load_yaml(args.spec, yaml)
        deployment = load_yaml(DEPLOYMENT_SET, yaml)
    except (yaml.YAMLError, OSError) as e:
        say(f"[fail] could not read: {e}")
        return 1
    dep_q = questions_of(deployment)

    # resource question sets, keyed by directory name = the spec's resource key
    sets = {}
    titles = {}
    if os.path.isdir(RESOURCES):
        for fam in sorted(os.listdir(RESOURCES)):
            fam_dir = os.path.join(RESOURCES, fam)
            if not os.path.isdir(fam_dir):
                continue
            for res in sorted(os.listdir(fam_dir)):
                qs = os.path.join(fam_dir, res, 'questions.yaml')
                if os.path.isfile(qs):
                    try:
                        doc = load_yaml(qs, yaml)
                    except yaml.YAMLError as e:
                        say(f"[fail] {qs}: {e}")
                        return 1
                    sets[res] = questions_of(doc)
                    titles[res] = doc.get('title', res)

    ctx = spec.get('context') or {}
    R.environments = list(ctx.get('environments') or [])
    R.env_q = dep_q.get('environments', (None, None))[1]
    dep = spec.get('deployment') or {}
    resources = spec.get('resources') or {}
    # `<set>__<instance>` is a second resource of one kind (spec.md, "Several of a kind"):
    # it reads the questions of its set and is titled with its instance name.
    for res in resources:
        base, _, inst = res.partition('__')
        if inst and res not in sets and base in sets:
            sets[res] = sets[base]
            titles[res] = f"{titles.get(base, base)} ({inst})"
    head = spec.get('spec') or {}
    workload = ctx.get('workload') or head.get('id') or '?'
    at = str(head.get('at') or datetime.date.today())[:10]

    out = []
    w = out.append
    w(f"# {L['title'].format(workload=workload)}")
    w('')
    w(L['intro'])
    w('')
    w(L['as_of'].format(date=at, spec=os.path.basename(args.spec)))
    w('')

    # --- the system: context -------------------------------------------------
    w(f"## {L['context']}")
    w('')
    for key in ('environments', 'location', 'workload', 'subscription_id', 'resource_group_name', 'stage_isolation'):
        src = ctx if key in ctx else ({k: v.get('value') for k, v in dep.items() if isinstance(v, dict)} if key in dep else None)
        if src is not None and key in src and key in dep_q and not R.is_stage_map(src[key]):
            w(f"- {R.line(dep_q[key][1], src[key])}")   # per-stage values follow in their own section
    w('')

    # --- what differs between the stages ---------------------------------------
    stage_lines = []
    for key, v in ctx.items():
        if R.is_stage_map(v) and key in dep_q:
            stage_lines.append(R.line(dep_q[key][1], v))
    for qid, d in dep.items():
        if isinstance(d, dict) and R.is_stage_map(d.get('value')) and qid in dep_q:
            note = f" _({L['savings']})_" if d.get('non_production') == 'default' else ''
            stage_lines.append(R.line(dep_q[qid][1], d['value']) + note)
    for res, groups in resources.items():
        qset = sets.get(res, {})
        for gid, qs in (groups or {}).items():
            if not isinstance(qs, dict) or str(gid).startswith('_'):
                continue
            for qid, d in qs.items():
                if isinstance(d, dict) and R.is_stage_map(d.get('value')):
                    q = qset.get(qid, (None, None))[1]
                    note = f" _({L['savings']})_" if d.get('non_production') == 'default' else ''
                    stage_lines.append(f"{titles.get(res, res)}: {R.line(q, d['value'])}{note}")
    if len(R.environments) > 1:
        w(f"## {L['stages']}")
        w('')
        w(L['stages_intro'])
        w('')
        for line in stage_lines:
            w(f"- {line}")
        w('')

    # --- what follows from your answers --------------------------------------
    derived = {}  # deployment id -> [(resource, line)]
    for res, groups in resources.items():
        qset = sets.get(res, {})
        for gid, qs in (groups or {}).items():
            if not isinstance(qs, dict) or str(gid).startswith('_'):
                continue
            for qid, d in qs.items():
                if isinstance(d, dict) and d.get('source') == 'requirement':
                    src = str(d.get('derived_from', '')).split('.')[-1]
                    q = qset.get(qid, (None, None))[1]
                    derived.setdefault(src, []).append((res, R.line(q, d.get('value'))))

    w(f"## {L['answers']}")
    w('')
    for qid, (gid, q) in dep_q.items():
        if q.get('audience') != 'customer' or qid not in dep:
            continue
        d = dep[qid]
        if not isinstance(d, dict):
            continue
        src = d.get('source')
        how = L['sources'].get(src, src) if src in CUSTOMER_ANSWER_SOURCES else L['assumed_default']
        if src == 'stated':
            how = L['stated']
        elif src == 'asked':
            how = L['answered']
        elif src == 'carried':
            how = L['carried']
        w(f"- **{R.line(q, d.get('value'))}** _({how})_")
        for res, line in derived.get(qid, []):
            w(f"  - {L['derived']}, {titles.get(res, res)}: {line}")
    w('')

    # --- set by the rules ------------------------------------------------------
    def forced_note(d):
        fb = str(d.get('forced_by', ''))
        m = re.match(r'^deployment\.([a-z_]+)', fb)
        if m and m.group(1) in dep_q and m.group(1) in dep and isinstance(dep[m.group(1)], dict):
            return f" — {L['because']}: {R.line(dep_q[m.group(1)][1], dep[m.group(1)].get('value'))}"
        return f" — {L['because']}: `{fb}`" if fb else ''

    w(f"## {L['rules']}")
    w('')
    w(L['rules_intro'])
    w('')
    w(f"### {L['whole_system']}")
    w('')
    for qid, (gid, q) in dep_q.items():
        if q.get('audience') == 'customer' or qid not in dep or gid == 'context':
            continue
        d = dep[qid]
        if not isinstance(d, dict) or d.get('source') in ('overridden', 'assumed'):
            continue
        note = forced_note(d) if d.get('source') == 'forced' else ''
        w(f"- {R.line(q, d.get('value'))}{note}")
    w('')
    overridden, assumed = [], []
    for res, groups in resources.items():
        qset = sets.get(res, {})
        lines = []
        for gid, qs in (groups or {}).items():
            if not isinstance(qs, dict) or str(gid).startswith('_'):
                continue
            for qid, d in qs.items():
                if not isinstance(d, dict):
                    continue
                q = qset.get(qid, (None, None))[1]
                src = d.get('source')
                if src == 'overridden':
                    overridden.append((titles.get(res, res), R.line(q, d.get('value')), d.get('reason') or d.get('note') or d.get('departs_from') or ''))
                    continue
                if src == 'assumed':
                    assumed.append((f"resources.{res}.{gid}.{qid}", R.line(q, d.get('value'))))
                    continue
                if src == 'requirement':
                    continue
                note = forced_note(d) if src == 'forced' else ''
                lines.append(f"- {R.line(q, d.get('value'))}{note}")
        if lines:
            w(f"### {titles.get(res, res)}")
            w('')
            out.extend(lines)
            w('')

    # --- overridden ------------------------------------------------------------
    for qid, d in dep.items():
        if isinstance(d, dict) and d.get('source') == 'overridden' and qid in dep_q:
            overridden.insert(0, (L['whole_system'], R.line(dep_q[qid][1], d.get('value')), d.get('reason') or d.get('note') or d.get('departs_from') or ''))
    if overridden:
        w(f"## {L['overridden']}")
        w('')
        for where, line, reason in overridden:
            w(f"- {where}: {line}" + (f" _({L['reason']}: {reason})_" if reason else ''))
        w('')

    # --- open, assumed ---------------------------------------------------------
    opens = spec.get('open') or []
    if opens:
        w(f"## {L['open']}")
        w('')
        w(L['open_intro'])
        w('')
        for o in opens:
            if isinstance(o, dict):
                owner = o.get('owner')
                stages = o.get('environments') or []
                where = f" [{', '.join(R.stage_name(e) for e in stages)}]" if stages else ''
                w(f"- {o.get('question', o.get('key'))}{where}" + (f" _({L['owner']}: {owner})_" if owner else '') + f" — {L['blocks']}: {o.get('blocks', '?')}")
        w('')
    for qid, d in dep.items():
        if isinstance(d, dict) and d.get('source') == 'assumed' and qid in dep_q:
            assumed.insert(0, (f"deployment.{qid}", R.line(dep_q[qid][1], d.get('value'))))
    if assumed:
        w(f"## {L['assumed']}")
        w('')
        w(L['assumed_intro'])
        w('')
        for key, line in assumed:
            w(f"- {line} (`{key}`)")
        w('')

    # --- appendix --------------------------------------------------------------
    w(f"## {L['appendix']}")
    w('')
    w(f"| {L['key']} | {L['value']} | {L['source']} |")
    w('|---|---|---|')

    def cell(v):
        return json.dumps(v, ensure_ascii=False).replace('|', '\\|') if not isinstance(v, str) else v.replace('|', '\\|')

    for qid, d in dep.items():
        if isinstance(d, dict) and 'value' in d:
            w(f"| `deployment.{qid}` | {cell(d['value'])} | {L['sources'].get(d.get('source'), d.get('source'))} |")
    for res, groups in resources.items():
        for gid, qs in (groups or {}).items():
            if not isinstance(qs, dict) or str(gid).startswith('_'):
                continue
            for qid, d in qs.items():
                if isinstance(d, dict) and 'value' in d:
                    w(f"| `{res}.{gid}.{qid}` | {cell(d['value'])} | {L['sources'].get(d.get('source'), d.get('source'))} |")
    for key, d in (spec.get('wiring') or {}).items():
        if isinstance(d, dict) and 'value' in d:
            w(f"| `wiring.{key}` | {cell(d['value'])} | {L['sources'].get(d.get('source'), d.get('source'))} |")
    w('')

    target = args.out or os.path.join(os.path.dirname(os.path.abspath(args.spec)), 'infra-decisions.md')
    with open(target, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    say(f"[ ok ] {target} - language {lang}" + (f", {R.fallbacks} line(s) fell back to en" if R.fallbacks else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
