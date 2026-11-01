#!/usr/bin/env python3
"""Checks every render-map.yaml against the format and against its question set.

Read-only. A render-map.yaml (references/render-map.md) is what render_digest.py prints as the
attribute and the literal of each decision, so a wrong key or a value no answer can take
lands in generated code. For each file - every resources/<family>/<resource>/render-map.yaml,
or the paths given:

  1. `resource` equals the question set's; `modules` names a list per target, each
     coordinate in the form of its registry.
  2. `decisions` holds exactly the set's questions, `<group>.<question>`.
  3. Each decision is `not_rendered: <reason>` alone, or one entry per target and
     implementation: `terraform` and `bicep` always, `<target>_avm` exactly when `modules`
     lists a module for the target.
  4. Each entry has exactly one of `attribute`, `gap` or `on_part`, only known fields; `values` keys are
     answers the question accepts; `format` carries `{value}`, names only other questions as
     `{group.question}` (beside `values`, `{value}` is the mapped fragment); `values` has a
     literal (or null) for every answer; an enum, bool, int or string answer has `values`,
     `format` or `passthrough: true`, never nothing; `part_of` points at a decision whose
     format names this one; `module` is one of the target's modules or companions;
     `omit_empty` is true and stands beside passthrough or format; `authored_when` lists
     answers of the question, on a module entry only, and `values` needs no literal for them;
     `on_part` stands on a question that references a part (a subnet) and carries `{part}`
     and `{self}`, with nothing that makes a literal beside it.
  5. Code (values exprs, also lines, a format of code) names only questions of the set as
     `{group.question}` and holds no `...` sketch.
  6. A list of entries over several modules names the module on each; `by_kind` keys are
     answers of the question `kinds` names, and only with `kinds` declared.
  7. Every decision that renders something says how an import reads it back (`import:`):
     a path in the Resource Graph row with `values` (literal -> an answer it accepts),
     `passthrough` or a `format` with one `{value}`; `cases` over several paths, each
     `when` with an answer; `not_readable: <reason>`; or `todo: <what is missing>`. The
     count of each is printed - `todo` is the work list, not a failure.

Without paths, a resource directory that has a questions.yaml and no render-map.yaml is an
error too: the digest has nothing to print for it.

Needs PyYAML (pip install pyyaml). Without it the script says so and exits 2.

Usage:
    python3 check_render_map.py [<render-map.yaml> ...]

Exit 0 every file valid, 1 a violation, 2 could not check.
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
RESOURCES = os.path.join(PLUGIN, 'resources')
REF_KINDS = os.path.join(PLUGIN, 'core', 'iac-authoring', 'references', 'ref-kinds.yaml')

TARGETS = ['terraform', 'bicep']
COORD = {
    'terraform': re.compile(r'^Azure/avm-(res|ptn)-[a-z0-9-]+/azurerm(//modules/[a-z0-9_-]+)?$'),
    'bicep': re.compile(r'^avm/(res|ptn)/[a-z0-9-]+(/[a-z0-9-]+)+$'),
}
ENTRY_FIELDS = {'attribute', 'values', 'format', 'also', 'module', 'note', 'gap', 'part_of', 'passthrough',
                'omit_empty', 'authored_when', 'on_part'}
# Answer types a literal is written from. A reference (accepts: { ref }) resolves to an id and a
# list is written as the list, so neither needs to say how it renders.
SCALAR_TYPES = {'enum', 'bool', 'int', 'string'}
# How an import reads a decision back (references/render-map.md, "Reading it back").
IMPORT_PATH = re.compile(r'^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)*$')
IMPORT_FIELDS = {'path', 'values', 'passthrough', 'format', 'cases', 'missing', 'note'}
IMPORT_STATS = {'read': 0, 'not_readable': 0, 'todo': 0}


def answers_of(question):
    """The answers a question takes, or None when any value goes (int, string, list)."""
    if question.get('type') == 'bool':
        return [True, False]
    acc = question.get('accepts')
    return list(acc) if isinstance(acc, list) else None


def check_import(where, imp, question):
    """One decision's `import:` - a path with values, passthrough or format; cases; or a marker."""
    if not isinstance(imp, dict) or not imp:
        return [f"{where}: import is a mapping"]
    for marker in ('not_readable', 'todo'):
        if marker in imp:
            IMPORT_STATS[marker] += 1
            if set(imp) != {marker}:
                return [f"{where}: {marker} stands alone"]
            if not (isinstance(imp[marker], str) and imp[marker].strip()):
                return [f"{where}: {marker} carries its reason"]
            return []
    IMPORT_STATS['read'] += 1
    errs = []
    unknown = set(imp) - IMPORT_FIELDS
    if unknown:
        errs.append(f"{where}: unknown field(s) {', '.join(sorted(unknown))}")
    allowed = answers_of(question)

    def answer_ok(a, what):
        if allowed is not None and a not in allowed:
            errs.append(f"{where}: {what} {a!r} is not an answer of the question")

    if 'missing' in imp:
        answer_ok(imp['missing'], 'missing')
    if 'cases' in imp:
        if 'path' in imp or {'values', 'passthrough', 'format'} & set(imp):
            errs.append(f"{where}: cases stands beside no path, values, passthrough or format")
        cases = imp['cases']
        if not isinstance(cases, list) or not cases:
            return errs + [f"{where}: cases is a non-empty list of {{ when, answer }}"]
        for i, c in enumerate(cases):
            if not isinstance(c, dict) or set(c) != {'when', 'answer'}:
                errs.append(f"{where}: cases[{i}] is {{ when, answer }}")
                continue
            when = c['when']
            if not isinstance(when, dict) or not when or not all(isinstance(p, str) and IMPORT_PATH.match(p) for p in when):
                errs.append(f"{where}: cases[{i}].when maps paths of the Resource Graph row to literals")
            answer_ok(c['answer'], f"cases[{i}].answer")
        return errs
    path = imp.get('path')
    if not (isinstance(path, str) and IMPORT_PATH.match(path)):
        errs.append(f"{where}: import.path is a dotted path in the Resource Graph row (properties.publicNetworkAccess)")
    forms = [k for k in ('values', 'passthrough', 'format') if k in imp]
    if len(forms) != 1:
        return errs + [f"{where}: import has exactly one of values, passthrough or format"]
    if 'values' in imp:
        vals = imp['values']
        if not isinstance(vals, dict) or not vals:
            errs.append(f"{where}: import.values maps literals to answers")
        else:
            for a in vals.values():
                answer_ok(a, 'import.values answer')
    elif 'passthrough' in imp and imp['passthrough'] is not True:
        errs.append(f"{where}: import.passthrough is true or absent")
    elif 'format' in imp and not (isinstance(imp['format'], str) and imp['format'].count('{value}') == 1
                                  and imp['format'].count('{') == 1):
        errs.append(f"{where}: import.format carries one {{value}} and nothing else in braces")
    return errs
TOP_FIELDS = {'schema_version', 'resource', 'modules', 'companions', 'kinds', 'import_parts', 'decisions'}
ARM_TYPE = re.compile(r'^[A-Za-z]+(\.[A-Za-z]+)+/[A-Za-z]+(/[A-Za-z]+)*$')
# `{group.question}`: another answer of the same resource. `${var.x}` is target code, not one.
PLACEHOLDER = re.compile(r'(?<!\$)\{([a-z0-9_]+\.[a-z0-9_]+)\}')


_PART_KINDS = None


def part_kinds(yaml):
    """ref-kinds.yaml's kind -> its part (None where the kind is a whole resource)."""
    global _PART_KINDS
    if _PART_KINDS is None:
        with open(REF_KINDS, encoding='utf-8') as f:
            _PART_KINDS = {k: (v or {}).get('part') for k, v in ((yaml.safe_load(f) or {}).get('kinds') or {}).items()}
    return _PART_KINDS


def check_entry(where, entry, question, ctx, mods):
    errs = []
    if not isinstance(entry, dict):
        return [f"{where}: an entry is a mapping"]
    unknown = set(entry) - ENTRY_FIELDS
    if unknown:
        errs.append(f"{where}: unknown field(s) {', '.join(sorted(unknown))}")
    if sum(k in entry for k in ('attribute', 'gap', 'on_part')) != 1:
        errs.append(f"{where}: needs exactly one of attribute, gap or on_part")
    for k in ('attribute', 'gap', 'note', 'part_of', 'on_part'):
        if k in entry and not (isinstance(entry[k], str) and entry[k].strip()):
            errs.append(f"{where}: {k} is a non-empty string")
    fmt = entry.get('format')
    if isinstance(fmt, dict):
        fmt = fmt.get('expr') if set(fmt) == {'expr'} else None
        if fmt is None:
            errs.append(f"{where}: format is a string or {{ expr: '<code>' }}")
    elif 'format' in entry and not (isinstance(fmt, str) and fmt.strip()):
        errs.append(f"{where}: format is a string or {{ expr: '<code>' }}")
        fmt = None
    if isinstance(fmt, str):
        if '{value}' not in fmt:
            errs.append(f"{where}: format carries no {{value}}")
        for ref in PLACEHOLDER.findall(fmt):
            if ref not in ctx['questions'] or ref == ctx['key']:
                errs.append(f"{where}: format names {{{ref}}}, not another question of the set")
    # A `{group.question}` in code - a values expr or an also line - names another question too.
    code = [lit['expr'] for lit in (entry.get('values') or {}).values()
            if isinstance(lit, dict) and isinstance(lit.get('expr'), str)]
    code += [line for line in (entry.get('also') or {}).values() if isinstance(line, str)]
    if isinstance(fmt, str) and isinstance(entry.get('format'), dict):
        code.append(fmt)
    for text in code:
        for ref in PLACEHOLDER.findall(text):
            if ref not in ctx['questions']:
                errs.append(f"{where}: {{{ref}}} is not a question of the set")
        # A sketch is not code: what the render fills in is named, `<name>`, never `...`.
        if '...' in text:
            errs.append(f"{where}: '...' in code - name what the render fills in as <name>")
    if 'passthrough' in entry and entry['passthrough'] is not True:
        errs.append(f"{where}: passthrough is true or absent")
    if 'omit_empty' in entry and (entry['omit_empty'] is not True or 'values' in entry or 'gap' in entry):
        errs.append(f"{where}: omit_empty is true, beside passthrough or format - values says left out itself")
    if 'passthrough' in entry and any(k in entry for k in ('values', 'format', 'gap', 'part_of')):
        errs.append(f"{where}: passthrough stands beside none of values, format, gap, part_of")
    accepts = question.get('accepts')
    scalar = question.get('type') in SCALAR_TYPES and not (isinstance(accepts, dict) and 'ref' in accepts)
    if scalar and 'attribute' in entry and not any(k in entry for k in ('values', 'format', 'part_of', 'passthrough')):
        errs.append(f"{where}: a {question.get('type')} answer needs values, format, or passthrough: true "
                    "(the attribute takes the answer as it is)")
    # on_part: the line this resource sets on a part another resource owns (an NSG on a subnet).
    # The question references that part; the digest fills {part} with its name, {self} with this
    # resource's id, and prints the line under the part's resource.
    on_part = entry.get('on_part')
    if isinstance(on_part, str):
        kind = accepts.get('ref') if isinstance(accepts, dict) else None
        if kind is None or not ctx['part_kinds'].get(kind):
            errs.append(f"{where}: on_part on a question that references no part (accepts: {{ ref: <kind with a part> }})")
        for ph in ('{part}', '{self}'):
            if ph not in on_part:
                errs.append(f"{where}: on_part carries no {ph}")
        if any(k in entry for k in ('values', 'format', 'passthrough', 'part_of', 'omit_empty', 'also')):
            errs.append(f"{where}: on_part stands beside none of values, format, passthrough, part_of, omit_empty, also")
    part = entry.get('part_of')
    if isinstance(part, str):
        formats = [e.get('format', '') for e in ctx['entries_of'](part)]
        if not any(f"{{{ctx['key']}}}" in f for f in formats if isinstance(f, str)):
            errs.append(f"{where}: part_of {part}, whose format does not name {{{ctx['key']}}}")

    if question.get('type') == 'bool':
        allowed = {True, False}
    elif isinstance(accepts, list):
        allowed = set(accepts)
    else:
        allowed = None
    for k in ('values', 'also'):
        m = entry.get(k)
        if m is None:
            continue
        if not isinstance(m, dict) or not m:
            errs.append(f"{where}: {k} is a non-empty mapping")
            continue
        if allowed is None:
            errs.append(f"{where}: {k} on a question that is neither an enum nor a bool")
            continue
        for ans in m:
            if ans not in allowed:
                errs.append(f"{where}: {k} key {ans!r} is not an answer the question accepts")
        if k == 'values':
            for ans, lit in m.items():
                if isinstance(lit, dict) and set(lit) != {'expr'}:
                    errs.append(f"{where}: values[{ans!r}] - a mapping literal is {{ expr: '<code>' }}")
            # Every answer has its literal, or null for "left out": an answer missing here would
            # otherwise reach the render with nothing said about it.
            for ans in sorted(allowed - set(m) - set(entry.get('authored_when') or []), key=str):
                errs.append(f"{where}: values has no literal for {ans!r} (null when it leaves the attribute out)")
        else:
            for ans, line in m.items():
                if not (isinstance(line, str) and line.strip()):
                    errs.append(f"{where}: also[{ans!r}] is a line of code")
    if 'module' in entry and entry['module'] not in mods:
        errs.append(f"{where}: module {entry['module']} is neither in modules nor in companions for the target")
    # Answers the module refuses: the resource renders authored for them. Only a module entry has one.
    aw = entry.get('authored_when')
    if aw is not None:
        if not ctx.get('is_avm'):
            errs.append(f"{where}: authored_when belongs on a module (_avm) entry")
        if not isinstance(aw, list) or not aw:
            errs.append(f"{where}: authored_when is a non-empty list of answers")
        elif allowed is not None:
            for ans in aw:
                if ans not in allowed:
                    errs.append(f"{where}: authored_when {ans!r} is not an answer the question accepts")
    return errs


def check_target(where, node, question, ctx, mods, nested=False):
    """An entry, a list of entries (one per module), or `by_kind` - a map from the kind
    question's answers to an entry or a list."""
    if isinstance(node, list):
        if not node:
            return [f"{where}: an empty list"]
        errs = []
        # One decision setting several attributes of one call, or carried by several modules:
        # then every element names its module, or a reader cannot tell which call it belongs to.
        named = {e.get('module') for e in node if isinstance(e, dict)}
        for i, e in enumerate(node):
            if not isinstance(e, dict):
                errs.append(f"{where}[{i}]: an entry is a mapping")
            elif len(named) > 1 and None in named:
                errs.append(f"{where}[{i}]: a list over several modules names the module on every entry")
            errs.extend(check_entry(f"{where}[{i}]", e, question, ctx, mods))
        return errs
    if isinstance(node, dict) and 'by_kind' in node:
        if nested:
            return [f"{where}: by_kind does not nest"]
        if set(node) != {'by_kind'}:
            return [f"{where}: by_kind stands alone"]
        if not ctx['kinds']:
            return [f"{where}: by_kind without a top-level kinds"]
        by = node['by_kind']
        if not isinstance(by, dict) or not by:
            return [f"{where}: by_kind is a non-empty mapping"]
        errs = []
        for kind, sub in by.items():
            if kind not in ctx['kinds']:
                errs.append(f"{where}: by_kind key {kind!r} is not an answer of the kind question")
            else:
                errs.extend(check_target(f"{where}.by_kind.{kind}", sub, question, ctx, mods, nested=True))
        return errs
    return check_entry(where, node, question, ctx, mods)


def coordinates(errs, rel, doc, field, required):
    """`modules` or `companions` as {target: [coordinates]}, reporting what is malformed."""
    raw = doc.get(field)
    if raw is None and not required:
        return {t: [] for t in TARGETS}
    if not isinstance(raw, dict) or not set(raw) <= set(TARGETS) or (required and set(raw) != set(TARGETS)):
        errs.append(f"{rel}: {field} names a list for terraform and for bicep")
        return {t: [] for t in TARGETS}
    out = {}
    for t in TARGETS:
        lst = raw.get(t, [])
        if not isinstance(lst, list):
            errs.append(f"{rel}: {field}.{t} is a list ([] when the target has none)")
            lst = []
        for c in lst:
            if not (isinstance(c, str) and COORD[t].match(c)):
                errs.append(f"{rel}: {field}.{t}: {c!r} is not a {t} AVM coordinate")
        out[t] = [c for c in lst if isinstance(c, str)]
    return out


def check_file(path, yaml):
    errs = []
    rel = os.path.relpath(path, PLUGIN).replace(os.sep, '/')
    qpath = os.path.join(os.path.dirname(path), 'questions.yaml')
    try:
        with open(path, encoding='utf-8') as f:
            doc = yaml.safe_load(f) or {}
        with open(qpath, encoding='utf-8') as f:
            qs = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        return [f"{rel}: cannot read it or its questions.yaml: {e}"]
    if not isinstance(doc, dict):
        return [f"{rel}: not a mapping"]

    unknown = set(doc) - TOP_FIELDS
    if unknown:
        errs.append(f"{rel}: unknown top-level field(s) {', '.join(sorted(unknown))}")
    if doc.get('schema_version') != 1:
        errs.append(f"{rel}: schema_version is 1")
    if doc.get('resource') != qs.get('resource'):
        errs.append(f"{rel}: resource {doc.get('resource')!r} is not the question set's {qs.get('resource')!r}")

    modules = coordinates(errs, rel, doc, 'modules', required=True)
    companions = coordinates(errs, rel, doc, 'companions', required=False)
    for t in TARGETS:
        for c in sorted(set(modules[t]) & set(companions[t])):
            errs.append(f"{rel}: {c} is in modules and in companions")

    # The other Azure resources an import adopts with this one (adopt.parts in the spec).
    if 'import_parts' in doc:
        parts = doc['import_parts']
        if not isinstance(parts, list) or not parts or not all(isinstance(t, str) and ARM_TYPE.match(t) for t in parts):
            errs.append(f"{rel}: import_parts is a list of ARM types (Microsoft.Web/serverFarms)")
        elif len(set(parts)) != len(parts) or doc.get('resource') in parts:
            errs.append(f"{rel}: import_parts lists a type twice or the set's own resource")

    questions = {f"{g.get('id')}.{q.get('id')}": q
                 for g in qs.get('groups') or [] for q in g.get('questions') or []}
    kinds = []
    if 'kinds' in doc:
        raw = doc.get('kinds')
        kq = raw.get('question') if isinstance(raw, dict) else None
        if not isinstance(raw, dict) or set(raw) != {'question'} or kq not in questions:
            errs.append(f"{rel}: kinds is {{ question: <group.question> }}, a question of the set")
        elif not isinstance(questions[kq].get('accepts'), list):
            errs.append(f"{rel}: kinds.question {kq} is not an enum")
        else:
            kinds = list(questions[kq]['accepts'])

    decisions = doc.get('decisions')
    if not isinstance(decisions, dict):
        return errs + [f"{rel}: decisions is a mapping"]

    def entries_of(key):
        """Every entry under a decision, through lists and by_kind - for part_of."""
        node = decisions.get(key)
        stack = [v for k, v in node.items() if k not in ('not_rendered', 'import')] if isinstance(node, dict) else []
        out = []
        while stack:
            n = stack.pop()
            if isinstance(n, list):
                stack.extend(n)
            elif isinstance(n, dict) and isinstance(n.get('by_kind'), dict):
                stack.extend(n['by_kind'].values())
            elif isinstance(n, dict):
                out.append(n)
        return out

    for key in questions:
        if key not in decisions:
            errs.append(f"{rel}: {key} missing - every question has an entry or not_rendered")
    for key, node in decisions.items():
        if key not in questions:
            errs.append(f"{rel}: {key} is not a question of the set")
            continue
        where = f"{rel}: {key}"
        if not isinstance(node, dict):
            errs.append(f"{where}: a mapping")
            continue
        if 'not_rendered' in node:
            if set(node) != {'not_rendered'}:
                errs.append(f"{where}: not_rendered stands alone")
            elif not (isinstance(node['not_rendered'], str) and node['not_rendered'].strip()):
                errs.append(f"{where}: not_rendered carries its reason")
            continue
        expected = set(TARGETS) | {f"{t}_avm" for t in TARGETS if modules[t]}
        for k in sorted(expected - set(node)):
            errs.append(f"{where}: {k} missing")
        if 'import' not in node:
            errs.append(f"{where}: import missing - how an import reads it back, or not_readable / todo")
        else:
            errs.extend(check_import(f"{where}.import", node['import'], questions[key]))
        for k in sorted(set(node) - expected - {'import'}):
            hint = ' (modules lists none for that target)' if k.endswith('_avm') else ''
            errs.append(f"{where}: {k} not expected{hint}")
        ctx = {'questions': questions, 'key': key, 'kinds': kinds, 'entries_of': entries_of,
               'part_kinds': part_kinds(yaml)}
        for k in sorted(set(node) & expected):
            t = k[:-4] if k.endswith('_avm') else k
            mods = (modules[t] if k.endswith('_avm') else []) + companions[t]
            ctx['is_avm'] = k.endswith('_avm')
            errs.extend(check_target(f"{where}.{k}", node[k], questions[key], ctx, mods))
    return errs


def main():
    ap = argparse.ArgumentParser(description='Check render-map.yaml files against the format and their question sets.')
    ap.add_argument('paths', nargs='*', help='render-map.yaml files (default: every one under resources/)')
    args = ap.parse_args()

    try:
        import yaml
    except ImportError:
        print('[fail] no YAML parser available - pip install pyyaml')
        return 2
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    errs, files = [], []
    if args.paths:
        files = [os.path.abspath(p) for p in args.paths]
    else:
        for root, _, names in os.walk(RESOURCES):
            if 'questions.yaml' not in names:
                continue
            if 'render-map.yaml' in names:
                files.append(os.path.join(root, 'render-map.yaml'))
            else:
                errs.append(f"{os.path.relpath(root, PLUGIN).replace(os.sep, '/')}: no render-map.yaml")
    for p in sorted(files):
        errs.extend(check_file(p, yaml))

    for e in errs:
        print(f"[fail] {e}")
    print(f"{len(files)} render-map.yaml file(s), {len(errs)} violation(s)")
    s = IMPORT_STATS
    print(f"import: {s['read']} read back, {s['not_readable']} not readable, {s['todo']} todo")
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())
