#!/usr/bin/env python3
"""Prints what a render needs from a spec and the references, instead of reading them whole.

Read-only. A render that reads the skill, spec.md, the idiom, naming, code structure, avm.md
and every resource's rendering reference in full spends well over 100 KB before the first
line of code, most of it on the other target, rationale and sections the spec does not use.
This digest reads the spec and prints:

  1. The shape: target, stages, language, granularity, the module split, delivery, the
     resource groups.
  2. What to read, and only that: each reference with the line ranges that apply to this
     spec (the other target's sections, unused branches and the rationale left out), and per
     resource the AVM part or the authored part of its rendering reference. The ranges are
     computed from the current files, so a moved heading never sends a run to the wrong line.
  3. Every deployment and context value with its source.
  4. Per resource: the AVM modules and the naming identifier, and every decision as
     `<resource>.<group>.<question>` - the key a test asserts - with its value, its source and
     what its render-map.yaml entry says for the target and implementation: the attribute with
     the literal the value becomes, further lines, the note or the gap.
  5. Wiring, target overrides, the `assumed` values (an `ASSUMED:` marker in every stage
     file) and the `open:` entries (placeholders), then the checks with their paths.

spec.md is not read for a render; the digest says what it holds for this spec. Look a key
up there only when the digest does not explain it.

Needs PyYAML (pip install pyyaml). Without it the script says so and exits 2.

Usage:
    python3 render_digest.py <spec> [--target terraform|bicep]

--target overrides spec.target (a port). Exit 0 printed, 1 printed with a gap (a resource
without a question set, a render-map.yaml or a rendering reference, a decision its set or its
render-map.yaml does not have), 2 could not read the spec.
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.abspath(os.path.join(HERE, '..', '..'))
PLUGIN = os.path.abspath(os.path.join(CORE, '..'))
RESOURCES = os.path.join(PLUGIN, 'resources')
REFS = os.path.join(CORE, 'iac-rendering', 'references')
sys.path.insert(0, os.path.join(CORE, 'iac-authoring', 'scripts'))
import spec_ref  # noqa: E402 - a reference as {resource: <key>} or {existing: <kind>}

PIPELINE_FILES = {'github': 'github', 'azure_devops': 'ado', 'gitlab': 'gitlab', 'local': 'local'}
AUTHORED_MARK = '## Authored rendering'
AVM_MARK = '## With the AVM module'

# Headings a reading leaves out, by file, each with the condition under which it is left out.
# The test asserts every title still exists, so a renamed heading fails there, not silently here.
SKIPS = {
    'terraform-idiom.md': [
        ('### What does not port to Bicep unchanged', lambda s: True),
        ('### Azure Verified Modules are the default module', lambda s: s['all_authored']),
        ('### Grouped AVM calls', lambda s: s['granularity'] != 'per-family' or s['all_authored']),
        ('### Do not generate a module per resource by reflex', lambda s: s['granularity'] != 'per-resource'),
        ('## Referencing what the deployment does not own', lambda s: not s['existing_refs']),
    ],
    'bicep-idiom.md': [
        ('### Where Bicep modules differ from Terraform', lambda s: True),
        ('## Azure Verified Modules from the public registry', lambda s: s['all_authored']),
        ('### Grouped AVM calls', lambda s: s['granularity'] != 'per-family' or s['all_authored']),
        ('### Do not generate a module per resource by reflex', lambda s: s['granularity'] != 'per-resource'),
        ('## Referencing what the deployment does not own', lambda s: not s['existing_refs']),
    ],
    'naming.md': [
        ('## The mechanism', lambda s: s['target'] == 'bicep'),
        ('## Terraform', lambda s: s['target'] == 'bicep'),
        ('## Bicep', lambda s: s['target'] == 'terraform'),
    ],
    # A Bicep stage section builds on the Terraform one ("same header as above"), so only a
    # Terraform render leaves the other target out; Bicep skips what nothing refers back to.
    'pipelines.github.md': [
        ('### Validate steps - Bicep', lambda s: s['target'] == 'terraform'),
        ('## Stage workflow - Bicep', lambda s: s['target'] == 'terraform'),
    ],
    'pipelines.ado.md': [
        ('### Validate steps - Bicep', lambda s: s['target'] == 'terraform'),
        ('## Stage template - Bicep', lambda s: s['target'] == 'terraform'),
        ('## Terraform install', lambda s: s['target'] == 'bicep'),
    ],
    'pipelines.gitlab.md': [
        ('## Bicep', lambda s: s['target'] == 'terraform'),
    ],
    'pipelines.local.md': [
        ('## `deploy.ps1` - Bicep', lambda s: s['target'] == 'terraform'),
        ('## `deploy.ps1` - Terraform', lambda s: s['target'] == 'bicep'),
    ],
    'avm.md': [
        ('## Why modules first, and what it costs', lambda s: True),
        # The coordinate of every resource is printed below, from its own reference.
        ('### Modules for the resources this plugin knows', lambda s: True),
    ],
}


def flat(text):
    return ' '.join(str(text).split())


def show(v):
    """A value on one line, as YAML flow style."""
    import yaml
    if isinstance(v, (dict, list, bool)) or v is None:
        text = yaml.safe_dump(v, default_flow_style=True, width=10 ** 6, allow_unicode=True, sort_keys=False).strip()
        return text[:-4].strip() if text.endswith('\n...') else text
    return str(v)


def rel(path):
    """A path under the plugin as `<plugin>/...`; the header names the plugin root once."""
    return '<plugin>/' + os.path.relpath(path, PLUGIN).replace(os.sep, '/')


def source_text(src):
    if isinstance(src, dict) and len(src) == 1:
        (k, ref), = src.items()
        return f"{k} {show(ref)}"
    return show(src) if src is not None else '-'


def value_of(node):
    return node.get('value') if isinstance(node, dict) and 'value' in node else node


def is_stage_map(v, stages):
    return isinstance(v, dict) and bool(v) and set(map(str, v)) <= set(stages)


# --- references ------------------------------------------------------------

def headings(path):
    """[(line, level, title)] of a Markdown file, code fences skipped; lines are 1-based."""
    out, fence = [], False
    with open(path, encoding='utf-8') as f:
        lines = f.read().splitlines()
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith('```'):
            fence = not fence
            continue
        m = re.match(r'^(#{1,6})\s+(.*)$', line)
        if m and not fence:
            out.append((i, len(m.group(1)), m.group(2).strip()))
    return out, len(lines)


def ranges_without(path, titles):
    """The line ranges of a file with the sections whose heading starts with one of the titles
    left out (a section runs to the next heading of the same or a higher level)."""
    hs, total = headings(path)
    cut = []
    for idx, (line, level, title) in enumerate(hs):
        head = '#' * level + ' ' + title
        if any(head.startswith(t) for t in titles):
            end = total
            for line2, level2, _ in hs[idx + 1:]:
                if level2 <= level:
                    end = line2 - 1
                    break
            cut.append((line, end))
    keep, start = [], 1
    for a, b in sorted(cut):
        if a > start:
            keep.append((start, a - 1))
        start = max(start, b + 1)
    if start <= total:
        keep.append((start, total))
    return keep, total


def fmt_ranges(keep, total):
    if keep == [(1, total)]:
        return 'whole'
    return ', '.join(f"{a}-{b}" for a, b in keep)


def split_reference(path, implementation):
    """The ranges of a resource's rendering reference: up to `## Authored rendering` for an AVM
    call, the opening and everything from that heading for an authored one. None when the
    reference has no such heading - then it is read whole."""
    hs, total = headings(path)
    authored = next((l for l, lv, t in hs if lv == 2 and t == AUTHORED_MARK[3:]), None)
    if authored is None:
        return None, total
    if implementation == 'authored':
        avm = next((l for l, lv, t in hs if lv == 2 and t.startswith(AVM_MARK[3:])), None)
        keep = ([(1, avm - 1)] if avm and avm > 1 else []) + [(authored, total)]
        return keep, total
    return [(1, authored - 1)], total


def find_set(kind):
    if not os.path.isdir(RESOURCES):
        return None, None
    for family in sorted(os.listdir(RESOURCES)):
        p = os.path.join(RESOURCES, family, kind, 'questions.yaml')
        if os.path.isfile(p):
            return family, p
    return None, None


def literal(v, target):
    """An answer as the target writes it: a string quoted, a bool and a number bare, a list
    of those in brackets, an `{ expr }` verbatim."""
    if isinstance(v, dict) and set(v) == {'expr'}:
        return str(v['expr'])
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return f'"{v}"' if target == 'terraform' else f"'{v}'"
    if isinstance(v, list) and all(isinstance(x, (str, bool, int, float)) for x in v):
        return '[' + ', '.join(literal(x, target) for x in v) + ']'
    return show(v)


# `{group.question}`: another answer of the same resource. `${var.x}` is target code, not one.
PLACEHOLDER = re.compile(r'(?<!\$)\{([a-z0-9_]+\.[a-z0-9_]+)\}')


def at_stage(v, stage, stages):
    return v.get(stage) if stage is not None and is_stage_map(v, stages) else v


def fragment(rmap_decisions, ref, entry_key, answer, target):
    """What a `{group.question}` stands for: that decision's `values` literal for its answer,
    unquoted; else a list in the target's brackets, a scalar as it is; `?` when unanswered."""
    node = (rmap_decisions.get(ref) or {}).get(entry_key)
    entries = node if isinstance(node, list) else [node]
    for e in entries:
        if isinstance(e, dict) and isinstance(e.get('values'), dict) and not isinstance(answer, (dict, list))                 and answer in e['values']:
            hit = e['values'][answer]
            return '' if hit is None else (str(hit['expr']) if isinstance(hit, dict) else str(hit))
    if answer is None:
        return '?'
    return literal(answer, target) if isinstance(answer, list) else str(answer)


def fill(text, refs):
    return PLACEHOLDER.sub(lambda m: refs.get(m.group(1), m.group(0)), text)


def placeholders(entry):
    """Every `{group.question}` an entry's format, values exprs and also lines name."""
    texts = []
    fmt = entry.get('format')
    texts.append(fmt['expr'] if isinstance(fmt, dict) else (fmt or ''))
    texts += [lit['expr'] for lit in (entry.get('values') or {}).values() if isinstance(lit, dict)]
    texts += [line for line in (entry.get('also') or {}).values() if isinstance(line, str)]
    return list(dict.fromkeys(r for t in texts for r in PLACEHOLDER.findall(str(t))))


LEFT_OUT = '(left out)'


def rendered(entry, v, target, refs=None, ref=False):
    """The literal an entry gives answer v, or None when it passes no scalar through. `refs`
    fills the `{group.question}` placeholders. With `format` beside `values`, `{value}` is the
    answer's mapped fragment; a `format` of `{ expr }` is code, and takes a list answer too.
    `ref`: the question takes a reference, printed as the id the render resolves it to - a
    resource of the spec from its module, an existing one from the stage file's id parameter."""
    refs = refs or {}
    fmt = entry.get('format')
    code = isinstance(fmt, dict)
    if entry.get('omit_empty') and v in ('', None, []):
        return LEFT_OUT
    if ref and spec_ref.is_ref(v) and 'values' not in entry:
        if 'resource' in v:
            v = f"<id of {v['part']} in {v['resource']}>" if v.get('part') else f"<id of {v['resource']}>"
        else:
            v = f"<id of the existing {v['existing']}, a stage-file parameter>"
        if 'format' not in entry:
            return v
        if code:
            return fill(fmt['expr'], refs).replace('{value}', v)
    if isinstance(v, (dict, list)) and ('values' in entry or ('format' in entry and not code)):
        return None  # an answer values cannot key - a list, a reference object
    piece = v
    if 'values' in entry:
        if v not in entry['values']:
            return None
        piece = entry['values'][v]
        if piece is None:
            return LEFT_OUT
        if 'format' not in entry:
            return fill(literal(piece, target), refs) if isinstance(piece, dict) else literal(piece, target)
        piece = piece['expr'] if isinstance(piece, dict) else piece
    if 'format' in entry:
        text = fill(fmt['expr'] if code else fmt, refs)
        text = text.replace('{value}', literal(piece, target) if code and not isinstance(piece, str) else str(piece))
        return text if code else literal(text, target)
    if isinstance(v, (str, bool, int, float)):
        return literal(v, target)
    return None


def render_lines(entry, value, stages, target, ctx):
    """What the digest prints under a decision for one render-map.yaml entry. `ctx` carries the
    resource's other answers and its render-map decisions, for `{group.question}` placeholders."""
    if 'gap' in entry:
        lines = [f"gap: {flat(entry['gap'])}"]
        if entry.get('module'):
            lines.append(f"module: {entry['module']}")
        return lines
    attr = flat(entry['attribute'])
    refs = placeholders(entry)
    involved = [value] + [ctx['answers'].get(r) for r in refs]
    per_stage = any(is_stage_map(x, stages) for x in involved)

    def refs_at(st):
        return {r: fragment(ctx['decisions'], r, ctx['entry_key'], at_stage(ctx['answers'].get(r), st, stages), target)
                for r in refs}

    if entry.get('part_of'):
        lines = [f"renders: part of {entry['part_of']} ({attr}) - the literal is printed there"]
    else:
        is_ref = isinstance((ctx.get('question') or {}).get('accepts'), dict) and 'ref' in ctx['question']['accepts']
        lits = [(st, rendered(entry, at_stage(value, st, stages), target, refs_at(st), is_ref))
                for st in (stages if per_stage else [None])]
        if all(l is None for _, l in lits):
            lines = [f"renders: {attr}"]
        elif per_stage:
            lines = [f"renders: {attr} = " + ', '.join(f"{l} ({st})" for st, l in lits)]
        else:
            lines = [f"renders: {attr} = {lits[0][1]}"]
    also = entry.get('also') or {}
    for st in (stages if per_stage else [None]):
        v = at_stage(value, st, stages)
        if not isinstance(v, (dict, list)) and v in also:
            lines.append(f"also: {fill(also[v], refs_at(st))}" + (f" ({st})" if per_stage else ''))
    if entry.get('module'):
        lines.append(f"module: {entry['module']}")
    if entry.get('note'):
        lines.append(f"note: {flat(entry['note'])}")
    return list(dict.fromkeys(lines))


def resolve(node, ctx):
    """An entry key's node as a list of entries: a list as it is, `by_kind` narrowed to the
    resource's answer of the kind question, a single entry in a list of one. None when the
    kind has no entry; the kind's answer as the second value."""
    if isinstance(node, dict) and 'by_kind' in node:
        kind = ctx['answers'].get(ctx['kind_question'])
        sub = node['by_kind'].get(kind) if not isinstance(kind, (dict, list)) else None
        return (None if sub is None else (sub if isinstance(sub, list) else [sub])), kind
    return (node if isinstance(node, list) else [node]), None


# --- spec ------------------------------------------------------------------

def decisions_of(node, path=''):
    """[(key path, entry)] of every map carrying a `value` under a resource - the same walk as
    check_render_coverage.py, so the keys here are the keys the tests must name."""
    out = []
    if not isinstance(node, dict):
        return out
    if 'value' in node:
        return [(path, node)]
    for k, v in node.items():
        if str(k).startswith('_') or (k == 'meta' and path and '.' not in path):
            continue
        out.extend(decisions_of(v, f"{path}.{k}" if path else str(k)))
    return out


def main():
    ap = argparse.ArgumentParser(description='Print what a render needs from a spec and the references.')
    ap.add_argument('spec', help='the infra-spec.yaml to render')
    ap.add_argument('--target', choices=['terraform', 'bicep'], help='override spec.target (a port)')
    args = ap.parse_args()

    try:
        import yaml
    except ImportError:
        print('[fail] no YAML parser available - pip install pyyaml', file=sys.stderr)
        return 2
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        with open(args.spec, encoding='utf-8') as f:
            spec = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        print(f"[fail] cannot read {args.spec}: {e}", file=sys.stderr)
        return 2
    if not isinstance(spec, dict):
        print(f"[fail] {args.spec} is not a mapping", file=sys.stderr)
        return 2

    sys.path.insert(0, HERE)
    import rg_roles

    head = spec.get('spec') or {}
    ctx = spec.get('context') or {}
    dep = spec.get('deployment') or {}
    comp = spec.get('composition') or {}
    resources = spec.get('resources') or {}
    target = args.target or head.get('target') or 'terraform'
    stages = [str(s) for s in (ctx.get('environments') or ['development', 'test', 'production'])]
    module_source = value_of(dep.get('module_source')) or 'avm'
    mechanism = value_of(dep.get('deploy_mechanism')) or 'local'

    module_of = {}
    for m in comp.get('modules') or []:
        for key in m.get('contains') or []:
            module_of[key] = m

    def implementation(key):
        m = module_of.get(key) or {}
        return m.get('implementation') or ('authored' if module_source == 'authored' else 'avm')

    kinds = {}
    for key in resources:
        kind = str(key).split('__')[0]
        family, qpath = find_set(kind)
        kinds[key] = (kind, family, qpath)
    families = sorted({f for _, f, _ in kinds.values() if f})
    all_authored = bool(resources) and all(implementation(k) == 'authored' for k in resources)
    state = {
        'target': target,
        'granularity': comp.get('granularity') or 'single',
        'all_authored': all_authored,
        'network_ownership': value_of(dep.get('network_ownership')),
        # any { existing: <kind> } in the spec: its id is a variable / param from the stage files
        'existing_refs': any(isinstance(r, dict) and 'existing' in r
                             for node in [*dep.values(), *(d for res in (spec.get('resources') or {}).values() if isinstance(res, dict)
                                                          for g in res.values() if isinstance(g, dict) for d in g.values())]
                             if isinstance(node, dict) for r in spec_ref.items(node.get('value'))),
    }
    gaps = []
    out = []
    p = lambda line='': out.append(line)  # noqa: E731

    # ---- 1. shape
    p(f"== render digest: {os.path.abspath(args.spec)}")
    p(f"<plugin> = {PLUGIN.replace(os.sep, '/')}")
    p(f"spec {head.get('id')}  target={target}  plugin_version={head.get('plugin_version')}  "
      f"language={ctx.get('language', 'en')}")
    p(f"stages: {', '.join(stages)}  (one root, one stage file and one state per stage)")
    p(f"granularity: {state['granularity']}  module_source: {module_source}  families: {', '.join(families) or '-'}")
    for m in comp.get('modules') or []:
        line = f"  module {m.get('id')}: {', '.join(m.get('contains') or [])}"
        if m.get('implementation'):
            line += f"  implementation={m['implementation']}"
        if m.get('needs'):
            line += f"  needs={','.join(m['needs'])}"
        if m.get('outputs'):
            line += f"  outputs={','.join(m['outputs'])}"
        p(line)
    p(f"delivery: {mechanism}  auth={value_of(dep.get('pipeline_auth'))}  approvals={value_of(dep.get('pipeline_approvals'))}")
    roles_data = rg_roles.load(yaml)
    split = rg_roles.groups(roles_data, dep, resources)
    created = rg_roles.created(dep)
    layout = value_of(dep.get('resource_group_layout')) or 'single'
    groups = (['main'] if rg_roles.has_main(dep) else []) + split
    p(f"resource groups: layout={layout}  scheme={rg_roles.scheme_of(dep) if split else '-'}  "
      + '  '.join(f"{g}={rg_roles.mode(dep, g)}" for g in groups))
    p()

    # ---- 2. what to read
    p('-- read (only these ranges; anything else only for a question the digest leaves open)')

    def ref(name, titles=None):
        path = os.path.join(REFS, name)
        if not os.path.isfile(path):
            gaps.append(f"reference {name} missing")
            return
        keep, total = ranges_without(path, titles or [])
        p(f"  {rel(path)}  {fmt_ranges(keep, total)}")

    def skips(name):
        return [t for t, cond in SKIPS.get(name, []) if cond(state)]

    if not all_authored:
        ref('avm.md', skips('avm.md'))
    idiom = f"{target}-idiom.md"
    ref(idiom, skips(idiom))
    ref('naming.md', skips('naming.md'))
    ref('code-structure.md')
    ref('pipelines.md')
    platform = f"pipelines.{PIPELINE_FILES.get(mechanism, mechanism)}.md"
    ref(platform, skips(platform))
    if layout == 'split' or created:
        ref('resource-groups.md')
    wiring = spec.get('wiring') or {}
    if value_of(wiring.get('private_dns_zones')) or value_of(dep.get('private_dns_ownership')) == 'deployment':
        ref('private-dns-zones.md')
    if len(families) > 1:
        p('  (agents.md only in Subagents mode - iac-rendering step 13)')
    ref('gitignore.md')
    for key, (kind, family, qpath) in kinds.items():
        if not family:
            continue
        path = os.path.join(RESOURCES, family, kind, f"{target}.md")
        if not os.path.isfile(path):
            gaps.append(f"{key}: no rendering reference {family}/{kind}/{target}.md - say so in the hand-over")
            continue
        if any(k2 != key and kinds[k2][0] == kind for k2 in list(kinds)[: list(kinds).index(key)]):
            continue
        keep, total = split_reference(path, implementation(key))
        part = '' if keep is None else (' (authored part)' if implementation(key) == 'authored' else ' (AVM part)')
        p(f"  {rel(path)}  {fmt_ranges(keep or [(1, total)], total)}{part}")
    p()

    # ---- 3. deployment and context
    p('-- context (variables/parameters; a stage map goes into the stage files)')
    for k, v in ctx.items():
        p(f"  context.{k} = {show(v)}")
    p('-- deployment (inherited by every resource)')
    for k, v in dep.items():
        if isinstance(v, dict) and 'value' in v:
            tag = '  [per stage]' if is_stage_map(v['value'], stages) else ''
            p(f"  deployment.{k} = {show(v['value'])}  ({source_text(v.get('source'))}){tag}")
        else:
            p(f"  deployment.{k} = {show(v)}")
    p()

    # ---- 4. resources
    p('-- resources (every key below is asserted once, or marked not-testable with a reason)')
    sets = {}
    for key, node in resources.items():
        kind, family, qpath = kinds[key]
        impl = implementation(key)
        p(f"## {key}  [{family or '?'}]  module={(module_of.get(key) or {}).get('id', '-')}  implementation={impl}")
        if not qpath:
            gaps.append(f"{key}: no question set for '{kind}' - a missing set is said, never improvised")
            p('   no question set - renders unknown; say so, never improvise')
        else:
            if qpath not in sets:
                with open(qpath, encoding='utf-8') as f:
                    sets[qpath] = yaml.safe_load(f) or {}
            qs = sets[qpath]
            naming = qs.get('naming') or {}
            p(f"   naming: {naming.get('terraform' if target == 'terraform' else 'bicep')}  abbreviation={naming.get('abbreviation')}")
            render_path = os.path.join(os.path.dirname(qpath), 'render-map.yaml')
            rmap = None
            if os.path.isfile(render_path):
                if render_path not in sets:
                    with open(render_path, encoding='utf-8') as f:
                        sets[render_path] = yaml.safe_load(f) or {}
                rmap = sets[render_path]
            if rmap is None:
                gaps.append(f"{key}: no render-map.yaml for {family}/{kind} - read the reference's decision table")
                p("   no render-map.yaml - the reference's decision table is the mapping")
            else:
                coords = (rmap.get('modules') or {}).get(target) or []
                if impl == 'avm' and not coords:
                    p(f"   avm: none for {target} - render authored and record implementation: authored")
                    impl = 'authored'
                elif impl == 'avm':
                    p(f"   avm: {', '.join(coords)}  (versions looked up live)")
                companions = (rmap.get('companions') or {}).get(target) or []
                if companions:
                    p(f"   companions: {', '.join(companions)}"
                      "  (called beside the resource for the decisions that name them)")
            entry_key = f"{target}_avm" if impl == 'avm' else target
            index = {(g.get('id'), q.get('id')): q for g in qs.get('groups') or [] for q in g.get('questions') or []}
        meta = (node or {}).get('meta') if isinstance(node, dict) else None
        if isinstance(meta, dict) and isinstance(meta.get('purpose'), dict):
            p(f"   purpose: {flat(meta['purpose'].get('value', ''))}")
        own = decisions_of(node, str(key))
        ctx = {
            'answers': {'.'.join(pth.split('.')[1:3]): e.get('value') for pth, e in own},
            'decisions': (rmap or {}).get('decisions') or {} if qpath else {},
            'entry_key': entry_key if qpath else None,
            'kind_question': ((rmap or {}).get('kinds') or {}).get('question') if qpath else None,
        }
        for path, entry in own:
            parts = path.split('.')
            tag = '  [per stage]' if is_stage_map(entry.get('value'), stages) else ''
            p(f"   {path} = {show(entry.get('value'))}  ({source_text(entry.get('source'))}){tag}")
            if qpath and len(parts) >= 3:
                q = index.get((parts[1], parts[2]))
                if q is None and (parts[1], parts[2]) == ('placement', 'resource_group'):
                    # A spec key, not a question: the group role the resource departs into.
                    p('      placement: the resource goes into this group role (spec.md, resource groups)')
                elif q is None:
                    gaps.append(f"{path}: not a question of {family}/{kind}")
                    p('      not in the question set')
                elif rmap is not None:
                    node_map = (rmap.get('decisions') or {}).get(f"{parts[1]}.{parts[2]}")
                    if node_map is None:
                        gaps.append(f"{path}: not in {family}/{kind}/render-map.yaml")
                        p('      not in render-map.yaml')
                    elif 'not_rendered' in node_map:
                        p(f"      not rendered: {flat(node_map['not_rendered'])}")
                    elif entry_key not in node_map:
                        gaps.append(f"{path}: render-map.yaml has no {entry_key} entry")
                        p(f"      no {entry_key} entry in render-map.yaml")
                    else:
                        ctx['question'] = q
                        entries, kind = resolve(node_map[entry_key], ctx)
                        if entries is None:
                            p(f"      not rendered for {ctx['kind_question']} = {kind}")
                        for e in entries or []:
                            for line in render_lines(e, entry.get('value'), stages, target, ctx):
                                p(f"      {line}")
                        # An answer the module refuses: this resource renders authored instead.
                        v = entry.get('value')
                        answers = list(v.values()) if is_stage_map(v, stages) else [v]
                        refused = sorted({str(a) for e in entries or [] for a in answers
                                          if not isinstance(a, (dict, list)) and a in (e.get('authored_when') or [])})
                        if refused and entry_key != target and target in node_map:
                            p(f"      authored: the module refuses {', '.join(refused)} - render this resource "
                              "authored and record implementation: authored; its entry:")
                            authored, _ = resolve(node_map[target], ctx)
                            for e in authored or []:
                                for line in render_lines(e, v, stages, target, ctx):
                                    p(f"        {line}")
        if isinstance(node, dict) and node.get('_target_overrides'):
            p(f"   _target_overrides: {show(node['_target_overrides'])}")
    p()

    # ---- 5. wiring, overrides, assumed, open
    if wiring:
        p('-- wiring (the root, never a module: only it sees both ends)')
        for k, v in wiring.items():
            if isinstance(v, dict) and 'value' in v:
                p(f"  wiring.{k}  ({source_text(v.get('source'))})")
                items = v['value'] if isinstance(v['value'], list) else [v['value']]
                for item in items:
                    p(f"    - {show(item)}")
            else:
                p(f"  wiring.{k} = {show(v)}")
    if spec.get('_target_overrides'):
        p(f"-- _target_overrides: {show(spec['_target_overrides'])}")

    assumed = []

    def walk(node, path):
        if isinstance(node, dict):
            if node.get('source') == 'assumed' and 'value' in node:
                assumed.append((path, node['value']))
                return
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k))

    walk({k: spec.get(k) for k in ('deployment', 'resources', 'wiring') if spec.get(k)}, '')
    p('-- assumed (a stage-file parameter in every stage, marked `# ASSUMED: <key>`; refused for apply)')
    for path, v in assumed:
        p(f"  {path} = {show(v)}")
    if not assumed:
        p('  none - no ASSUMED marker in any stage file')
    p('-- open (the stage file is written anyway: ids 00000000-0000-0000-0000-000000000000, names OPEN-<what>)')
    for o in spec.get('open') or []:
        envs = ','.join(o.get('environments') or []) or 'all stages'
        p(f"  {o.get('key')}  [{envs}]  owner={o.get('owner')}  blocks={o.get('blocks')}")
        p(f"    {flat(o.get('question', ''))}")
    if not spec.get('open'):
        p('  none - no placeholder in any stage file')
    p()

    # ---- 6. the checks
    spec_abs = os.path.abspath(args.spec).replace(os.sep, '/')
    root = os.path.dirname(spec_abs)
    s = '<plugin>/core/iac-rendering/scripts'
    p('-- before handing over')
    p(f"  python {s}/write_naming.py {spec_abs}   (first, when the root has no naming.yaml)")
    if target == 'terraform':
        dirs = ['.'] + ([f"modules/{f}" for f in families] if state['granularity'] == 'per-family' else [])
        p(f"  terraform fmt -recursive; terraform validate; terraform test in {', '.join(dirs)}")
    else:
        p(f"  bicep build; python {s}/run_arm_tests.py")
    for cmd in ('check_render_coverage.py', 'check_code_structure.py', 'check_pipeline.py', 'list_names.py'):
        arg = root if cmd == 'check_code_structure.py' else spec_abs
        p(f"  python {s}/{cmd} {arg}")
    p(f"  python {s}/sync_claude_md.py <repo-root> --root <root> --write")

    if gaps:
        p()
        p('-- gaps (say each one in the hand-over)')
        for g in gaps:
            p(f"  {g}")
    print('\n'.join(out))
    return 1 if gaps else 0


if __name__ == '__main__':
    sys.exit(main())
