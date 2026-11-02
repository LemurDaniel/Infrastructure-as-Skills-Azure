#!/usr/bin/env python3
"""Writes an infra-spec.yaml in its canonical form, in place.

    python write_spec.py <infra-spec.yaml> [--check] [--no-stamp]

The run decides, this script lays the file out: the same decisions give the same file, and
a re-run is a diff of what moved, not of how it was typed.

  - sections in a fixed order (spec, context, deployment, pattern, composition, resources,
    wiring, unmapped, open); a decision's fields as value, source, forces;
  - deployment keys in the order of questions/deployment.yaml under one `# --- <group> ---`
    comment per group; a resource's groups and questions in the order of its question set,
    after `meta` and an import's `adopt`,
    one blank line between resources; a stage map in the order of context.environments.
    The resources themselves keep the order the run wrote them in: the decision document,
    the name list and the picture follow it, and the run puts what matters most first;
  - every map in block style, one key per line - a decision, a stage map, a source; only a
    short list of plain values on one line ([audit], [development, test, production]);
    never a YAML anchor;
  - spec.plugin_version stamped with the installed plugin (--no-stamp leaves it as it is);
  - the root's naming.yaml written beside the spec when it has none, by
    core/iac-rendering/scripts/write_naming.py (not with --check).

Nothing else changes. Every comment stays at the key it stood at, and the file is written
only if it reads back as the same content (plugin_version aside) with the same comments in
the same places - anything else stops the script and leaves the file untouched.

Exit 0 written or already canonical, 1 --check found a file that is not canonical,
2 not written (no parser, no file, a comment that cannot be placed, a content change).
Needs PyYAML.
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML is required: pip install pyyaml")
    sys.exit(2)

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
PLUGIN_JSON = PLUGIN / ".claude-plugin" / "plugin.json"
DEPLOYMENT_SET = HERE.parent / "questions" / "deployment.yaml"
WRITE_NAMING = PLUGIN / "core" / "iac-rendering" / "scripts" / "write_naming.py"

SECTIONS = ['schema_version', 'spec', 'context', 'deployment', 'pattern', 'composition', 'resources', 'wiring', 'unmapped',
            'open']
HEAD = ['id', 'target', 'generated_by', 'plugin_version', 'skill', 'skill_version', 'at', 'imported_from']
IMPORTED_FROM = ['scopes', 'tag_filter', 'read_at']
ADOPT = ['id', 'lock_id', 'diagnostic_setting_id', 'parts']
UNMAPPED = ['type', 'id', 'reason', 'note']
CONTEXT = ['environments', 'language', 'location', 'workload', 'subscription_id', 'resource_group_name', 'tags']
ENTRY = ['value', 'source', 'forces']
COMPOSITION = ['granularity', 'source', 'modules']
WIRING = ['private_dns_zones', 'role_assignments', 'access']
OPEN = ['key', 'environments', 'question', 'owner', 'blocks']
WIDTH = 120
GROUP_COMMENT = re.compile(r'^# --- .+ ---$')
KEY = re.compile(r"""^('(?:[^']|'')*'|"[^"]*"|[^\s#'"\[\]{},&*!|>%@`][^#]*?):(?:\s|$)""")


# --- order -------------------------------------------------------------------

def question_sets():
    """'deployment' or a set's directory name -> [(group id, [question ids])]."""
    def groups(path):
        doc = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        return [(g.get('id'), [q['id'] for q in g.get('questions') or [] if isinstance(q, dict) and q.get('id')])
                for g in doc.get('groups') or [] if isinstance(g, dict)]
    sets = {'deployment': groups(DEPLOYMENT_SET)}
    for qs in sorted((PLUGIN / 'resources').glob('*/*/questions.yaml')):
        sets[qs.parent.name] = groups(qs)
    return sets


def order(d, known):
    """The mapping with the known keys first, in that order (a `<known>_<suffix>` key beside
    its known key), the rest after them as they were."""
    if not isinstance(d, dict):
        return d

    def rank(k):
        for i, n in enumerate(known):
            if k == n or str(k).startswith(n + '_'):
                return i
        return len(known)
    return {k: d[k] for k in sorted(d, key=rank)}


def canonical(spec, sets):
    """The spec in canonical order, and the group comments to put above keys: path -> [lines]."""
    groups = {}
    envs = (spec.get('context') or {}).get('environments') if isinstance(spec.get('context'), dict) else None
    envs = envs if isinstance(envs, list) else []

    def entry(e):
        if not (isinstance(e, dict) and 'value' in e):
            return e
        e = order(e, ENTRY)
        v = e['value']
        if isinstance(v, dict) and v and set(v) <= set(envs):
            e['value'] = {s: v[s] for s in envs if s in v}
        return e

    def by_set(d, set_groups):
        """A resource's groups and questions in the order of its question set, `meta` first."""
        if not isinstance(d, dict):
            return d
        out = {}
        if isinstance(d.get('meta'), dict):
            out['meta'] = {q: entry(v) for q, v in d['meta'].items()}
        if isinstance(d.get('adopt'), dict):
            out['adopt'] = {q: entry(v) for q, v in order(d['adopt'], ADOPT).items()}
        for gid, ids in set_groups:
            g = d.get(gid)
            if isinstance(g, dict):
                out[gid] = {q: entry(g[q]) for q in ids if q in g}
                out[gid].update({q: entry(v) for q, v in g.items() if q not in out[gid]})
        for gid, g in d.items():
            if gid not in out:
                out[gid] = {q: entry(v) for q, v in g.items()} if isinstance(g, dict) else g
        return out

    out = order(spec, SECTIONS)
    out['spec'] = order(out.get('spec'), HEAD) if 'spec' in out else None
    if out['spec'] is None:
        del out['spec']
    elif isinstance(out['spec'].get('imported_from'), dict):
        out['spec']['imported_from'] = order(out['spec']['imported_from'], IMPORTED_FROM)
    if isinstance(out.get('context'), dict):
        out['context'] = {k: entry(v) for k, v in order(out['context'], CONTEXT).items()}

    dep = out.get('deployment')
    if isinstance(dep, dict):
        new = {}
        for gid, ids in sets['deployment'] + [('not in deployment.yaml', list(dep))]:
            first = True
            for q in ids:
                if q in dep and q not in new:
                    if first:
                        groups[('deployment', str(q))] = [f'# --- {gid} ---']
                        first = False
                    new[q] = entry(dep[q])
        out['deployment'] = new

    if isinstance(out.get('composition'), dict):
        out['composition'] = order(out['composition'], COMPOSITION)

    if isinstance(out.get('resources'), dict):
        out['resources'] = {key: by_set(r, sets.get(str(key).split('__')[0], []))
                            for key, r in out['resources'].items()}

    if isinstance(out.get('wiring'), dict):
        out['wiring'] = {k: entry(v) for k, v in order(out['wiring'], WIRING).items()}
    if isinstance(out.get('open'), list):
        out['open'] = [order(o, OPEN) for o in out['open']]
    if isinstance(out.get('unmapped'), list):
        out['unmapped'] = [order(u, UNMAPPED) for u in out['unmapped']]
    return out, groups


# --- comments ----------------------------------------------------------------

def split_comment(value):
    """'x  # note' -> ('x', '# note'); a quoted value's own '#' is not a comment."""
    start = 0
    if value[:1] in ("'", '"'):
        q, i = value[0], 1
        while i < len(value):
            if value[i] == q:
                if q == "'" and value[i + 1:i + 2] == "'":
                    i += 2
                    continue
                break
            i += 2 if (q == '"' and value[i] == '\\') else 1
        start = i + 1
    m = re.search(r'(^|\s)#', value[start:])
    if not m:
        return value.strip(), None
    at = start + m.start() + len(m.group(1))
    return value[:at].strip(), value[at:].strip()


def comments(text):
    """The comments of a block-style YAML file by the key path they stand at: comment lines
    above a key (leading) and a comment after a value on its line (trailing). The generated
    group comments are left out. A path is a tuple of keys (str) and list positions (int).
    A comment it cannot tie to a key is returned as unplaced; the comments above the first
    key are the file's own and stay on top, whichever key comes first after writing."""
    leading, trailing, pending, unplaced = {}, {}, [], []
    top = True
    stack, counters = [], {}          # stack: (column, key or list position)
    block, quote = None, None         # inside a block scalar (its key's column), a quoted scalar (its quote)
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.lstrip()
        col = len(line) - len(stripped)
        if block is not None:
            if not stripped or col > block:
                continue
            block = None
        if quote is not None:
            if _closes(quote, line):
                quote = None
            continue
        if not stripped:
            continue
        if stripped.startswith('#'):
            if not GROUP_COMMENT.match(stripped):
                pending.append(stripped)
            continue
        rest, dashed = stripped, False
        while True:
            m = re.match(r'-( +|$)', rest)
            if not m:
                break
            while stack and (stack[-1][0] > col or (stack[-1][0] == col and isinstance(stack[-1][1], int))):
                stack.pop()
            owner = tuple(e for _, e in stack)
            counters[owner] = counters.get(owner, -1) + 1
            stack.append((col, counters[owner]))
            col += m.end()
            rest = rest[m.end():]
            dashed = True
        m = KEY.match(rest)
        if m:
            while stack and stack[-1][0] >= col:
                stack.pop()
            key = m.group(1)
            if key[:1] in ("'", '"'):
                key = yaml.safe_load(key)
            stack.append((col, str(key)))
            value = rest[m.end():]
        elif dashed:
            value = rest
        else:                             # a folded scalar's next line
            if split_comment(rest)[1]:
                unplaced.append(stripped)
            continue
        path = tuple(e for _, e in stack)
        if pending:
            leading.setdefault(('<top>',) if top else path, []).extend(pending)
            pending = []
        top = False
        content, note = split_comment(value)
        if note:
            trailing[path] = note
        if content[:1] in ('|', '>'):
            block = stack[-1][0]
        elif content[:1] in ("'", '"') and not _closes(content[0], content[1:]):
            quote = content[0]
    if pending:
        leading.setdefault(('<end>',), []).extend(pending)
    return leading, trailing, unplaced


def _closes(quote, text):
    """Whether the text holds the closing quote of a quoted scalar."""
    if quote == "'":
        return "'" in text.replace("''", '')
    return re.search(r'(?<!\\)"', text) is not None


# --- emit --------------------------------------------------------------------

class Dumper(yaml.SafeDumper):
    """PyYAML's safe dumper, with a timestamp kept as it is usually typed (2026-10-17T09:14:00Z)."""


def _timestamp(dumper, value):
    text = value.isoformat()
    if isinstance(value, datetime.datetime) and value.utcoffset() == datetime.timedelta(0):
        text = text[:-len('+00:00')] + 'Z'
    return dumper.represent_scalar('tag:yaml.org,2002:timestamp', text)


Dumper.add_representer(datetime.datetime, _timestamp)


def dump(v, **kw):
    return yaml.dump(v, Dumper=Dumper, allow_unicode=True, sort_keys=False, **kw)


def flat(v):
    """One value as YAML on one line, the way PyYAML writes it."""
    s = dump(v, default_flow_style=True, width=float('inf'))
    return s[:-5] if s.endswith('\n...\n') else s.rstrip('\n')


def emit(spec, leading, trailing, groups):
    out = []
    noted = set(leading) | set(trailing)

    def has_notes(path):
        return any(len(p) > len(path) and p[:len(path)] == path for p in noted)

    def one_line(v, path, used):
        """Whether a collection goes on one line: a short list of plain values with no comment
        inside, at least two levels down. A map never - a decision, a stage map, a source -
        so every key reads down the page at its own indent."""
        if not isinstance(v, list) or not v or len(path) < 2 or has_notes(path):
            return False
        return all(not isinstance(i, (dict, list)) for i in v) and used + len(flat(v)) <= WIDTH

    def above(path, ind):
        for c in groups.get(path, []):
            if out and not out[-1].endswith(':'):
                out.append('')
            out.append(ind + c)
        for c in leading.get(path, []):
            out.append(ind + c)

    def leaf(lead, k, v, note):
        """key: value - a long string folded onto further lines the way PyYAML folds it."""
        text = f'{lead}{flat(k)}: {flat(v)}'
        if note or not isinstance(v, str) or len(text) <= WIDTH:
            out.append(text + (f'  {note}' if note else ''))
            return
        folded = dump({k: v}, width=WIDTH - len(lead))
        lines = folded.rstrip('\n').split('\n')
        out.append(lead + lines[0])
        out.extend(' ' * len(lead) + l for l in lines[1:])

    def mapping(d, path, ind, dash=None):
        for i, (k, v) in enumerate(d.items()):
            p = path + (str(k),)
            if (not path or (path == ('resources',) and i)) and out:
                out.append('')
            above(p, ind)
            lead = dash if (dash is not None and i == 0) else ind
            key = flat(k)
            note = trailing.get(p)
            tail = f'  {note}' if note else ''
            if isinstance(v, dict) and v and not one_line(v, p, len(lead) + len(key) + 2):
                out.append(f'{lead}{key}:{tail}')
                mapping(v, p, ind + '  ')
            elif isinstance(v, list) and v and not one_line(v, p, len(lead) + len(key) + 2):
                out.append(f'{lead}{key}:{tail}')
                sequence(v, p, ind)
            else:
                leaf(lead, k, v, note)

    def sequence(items, path, ind):
        for i, item in enumerate(items):
            p = path + (i,)
            above(p, ind)
            note = trailing.get(p)
            if isinstance(item, dict) and item and not one_line(item, p, len(ind) + 2):
                mapping(item, p, ind + '  ', dash=ind + '- ')
            elif isinstance(item, list) and item and not one_line(item, p, len(ind) + 2):
                out.append(f'{ind}-' + (f'  {note}' if note else ''))
                sequence(item, p, ind + '  ')
            else:
                out.append(f'{ind}- {flat(item)}' + (f'  {note}' if note else ''))

    out.extend(leading.get(('<top>',), []))
    mapping(spec, (), '')
    out.extend(leading.get(('<end>',), []))
    return '\n'.join(out) + '\n'


# --- main --------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description='Write an infra-spec.yaml in its canonical form, in place.')
    ap.add_argument('path', help='the infra-spec.yaml')
    ap.add_argument('--check', action='store_true',
                    help='write nothing, stamp nothing; exit 1 when the file is not canonical')
    ap.add_argument('--no-stamp', action='store_true', help='leave spec.plugin_version as it is')
    args = ap.parse_args()

    path = Path(args.path)
    if not path.is_file():
        print(f"no such file: {path}")
        return 2
    raw = path.read_bytes()
    newline = '\r\n' if b'\r\n' in raw else '\n'
    text = raw.decode('utf-8').replace('\r\n', '\n')
    try:
        spec = yaml.safe_load(text)
    except yaml.YAMLError as e:
        print(f"{path}: YAML does not parse: {e}")
        return 2
    if not isinstance(spec, dict):
        print(f"{path}: not a spec (no mapping at the top)")
        return 2

    if not (args.no_stamp or args.check) and isinstance(spec.get('spec'), dict):
        spec['spec']['plugin_version'] = json.loads(PLUGIN_JSON.read_text(encoding='utf-8'))['version']
    data, groups = canonical(spec, question_sets())
    leading, trailing, unplaced = comments(text)
    if unplaced:
        print(f"{path}: not written - a comment stands where no key can carry it: {unplaced[:3]}")
        return 2
    onto_first_key(data, leading, trailing)
    new = emit(data, leading, trailing, groups)

    if yaml.safe_load(new) != spec:
        print(f"{path}: not written - the canonical form would not read back as the same content")
        return 2
    kept_leading, kept_trailing, _ = comments(new)
    if (kept_leading, kept_trailing) != (leading, trailing):
        lost = [c for p, cs in leading.items() for c in cs if c not in kept_leading.get(p, [])]
        lost += [c for p, c in trailing.items() if kept_trailing.get(p) != c]
        print(f"{path}: not written - a comment could not be kept at its key: {lost[:3]}")
        return 2

    if new == text:
        print(f"{path}: canonical")
        return write_naming(path, args.check)
    if args.check:
        print(f"{path}: not canonical - run write_spec.py on it")
        return 1
    with open(path, 'w', encoding='utf-8', newline=newline) as f:
        f.write(new)
    kept = sum(len(c) for c in leading.values()) + len(trailing)
    print(f"{path}: written ({kept} comment(s) kept)")
    return write_naming(path, args.check)


def onto_first_key(data, leading, trailing):
    """A comment on a list item that is a map - `- { from: a, to: b }  # note` - moves to the
    item's first key: the item is written as a block, and its first line is that key's."""
    def at(p):
        node = data
        for k in p:
            try:
                node = node[k]
            except (KeyError, IndexError, TypeError):
                return None
        return node

    for notes in (leading, trailing):
        for p in [p for p in notes if p and isinstance(p[-1], int)]:
            item = at(p)
            if isinstance(item, dict) and item:
                target = p + (str(next(iter(item))),)
                if notes is trailing:
                    if target not in trailing:
                        trailing[target] = trailing.pop(p)
                else:
                    leading[target] = leading.pop(p) + leading.get(target, [])


def write_naming(path, check):
    """The root's naming.yaml belongs with the spec: written here when missing, never replaced."""
    if check:
        return 0
    p = subprocess.run([sys.executable, str(WRITE_NAMING), str(path)], capture_output=True, text=True)
    print((p.stdout or p.stderr).rstrip())
    return 0 if p.returncode == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
