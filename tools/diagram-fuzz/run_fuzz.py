#!/usr/bin/env python3
"""Aesthetics fuzzer for new_diagram.py: random valid specs in, layout metrics out.

Specs are mutated from the fixtures (resource blocks reused, wiring and exposure re-rolled),
rendered with new_diagram.py, checked with verify_diagram.py, and scored on the geometry of the
.drawio itself - no PNG export, no draw.io install, so it runs in CI or on a small App Service.

    python run_fuzz.py --n 200 --seed 1                 # report, exit 1 on a hard violation
    python run_fuzz.py --n 50 --keep-worst 5 --out ./fuzz-out
    python run_fuzz.py --n 20 --seed 1 --max-score 40   # also fail when the mean score is above

Hard violations (always fail): script crash, verify mismatch, two icons overlapping, a call
between two shapes of one container that leaves it. Soft metrics (scored, lower is better): edge crossings, edges running through
a foreign icon, edge length, label wider than its box, aspect ratio.
The edge model is the straight line through the waypoints, or centre to centre without any;
that is a proxy for the orthogonal routing draw.io does, good for ranking, not for exact counts.

Needs PyYAML. Exit 0 ok, 1 a violation or the score gate, 2 could not run.
"""

import argparse
import copy
import glob
import json
import os
import random
import re
import statistics
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
DIAGRAM = os.path.join(HERE, '..', '..', 'plugins', 'infrastructure-as-skills-azure', 'core', 'iac-diagram')
SCRIPTS = os.path.join(DIAGRAM, 'scripts')
FIXTURES = os.path.join(DIAGRAM, 'tests', 'fixtures')
NEW, VERIFY = (os.path.join(SCRIPTS, n) for n in ('new_diagram.py', 'verify_diagram.py'))

EXTERNALS = ['entra-id', 'sharepoint-online', 'github', 'on-prem']
# Kinds that make sense as a target of a call; the sources are the compute kinds.
SOURCES = ['app-service', 'function-app', 'container-apps']
ENTRY_LABELS = ['HTTPS 443', 'OIDC', 'Graph 443', '', '']


def load_pool():
    import yaml
    docs, blocks = [], {}
    for f in sorted(glob.glob(os.path.join(FIXTURES, '*.yaml'))):
        with open(f, encoding='utf-8') as fh:
            d = yaml.safe_load(fh)
        docs.append(d)
        for k, v in (d.get('resources') or {}).items():
            blocks.setdefault(k, v)
    return docs, blocks


def generate(rng, docs, blocks, seed):
    spec = copy.deepcopy(rng.choice(docs))
    kinds = [k for k in blocks if '__' not in k and k not in ('virtual-network', 'log-analytics-workspace', 'blob-container')]
    picked = rng.sample(kinds, rng.randint(2, min(14, len(kinds))))
    if not any(k in picked for k in SOURCES):
        picked.append(rng.choice([k for k in SOURCES if k in blocks]))
    res = {}
    if rng.random() < 0.7 and 'virtual-network' in blocks:
        res['virtual-network'] = copy.deepcopy(blocks['virtual-network'])
    for k in picked:
        res[k] = copy.deepcopy(blocks[k])
    if 'log-analytics-workspace' in blocks and rng.random() < 0.6:
        res['log-analytics-workspace'] = copy.deepcopy(blocks['log-analytics-workspace'])
    spec['resources'] = res

    sources = [k for k in res if k in SOURCES]
    targets = [k for k in res if k not in SOURCES and k not in ('front-door', 'application-gateway') and k not in ('virtual-network', 'log-analytics-workspace')]
    entry = rng.choice(sources)
    # An edge kind is drawn on the line from the internet; unwired it is not drawn at all.
    edges = [k for k in ('front-door', 'application-gateway') if k in res]
    chain = ['users'] + edges + [entry]
    access = [{'from': a, 'to': b, 'label': rng.choice(ENTRY_LABELS[:3])} for a, b in zip(chain, chain[1:])]
    for s_ in sources:
        for t in rng.sample(targets, rng.randint(0, len(targets))):
            access.append({'from': s_, 'to': t})
        if rng.random() < 0.4:
            access.append({'from': s_, 'to': 'external:' + rng.choice(EXTERNALS), 'label': rng.choice(ENTRY_LABELS)})
    # Calls between the compute resources: a request that fans out (a dashboard starting runs).
    if len(sources) > 1 and rng.random() < 0.6:
        for t in rng.sample([x for x in sources if x != entry], rng.randint(1, len(sources) - 1)):
            access.append({'from': entry, 'to': t, 'label': rng.choice(['Run starten', 'Pruefung', ''])})
    for a in access:
        if not a.get('label'):
            a.pop('label', None)
    wiring = spec.setdefault('wiring', {})
    wiring['access'] = {'value': access, 'source': 'stated'}
    wiring['purposes'] = {'value': {k: f'Purpose of {k}' for k in res if rng.random() < 0.6}, 'source': 'stated'}
    wiring['optional'] = {'value': [k for k in targets if rng.random() < 0.15], 'source': 'stated'}
    wiring.pop('role_assignments', None)
    spec['context']['language'] = rng.choice(['en', 'de'])
    spec['context']['environments'] = rng.choice([['production'], ['test', 'production'], ['development', 'test', 'production']])
    spec['spec']['id'] = f'fuzz-{seed}'
    spec.pop('open', None)
    return spec


# --- geometry ------------------------------------------------------------

def read_cells(path):
    cells = {}
    for c in ET.parse(path).getroot().iter('mxCell'):
        if c.get('id') in ('0', '1'):
            continue
        g = c.find('mxGeometry')
        cell = {'id': c.get('id'), 'style': c.get('style') or '', 'value': c.get('value') or '', 'parent': c.get('parent'),
                'edge': c.get('edge') == '1', 'source': c.get('source'), 'target': c.get('target'), 'pts': []}
        if g is not None:
            cell['geo'] = [float(g.get(k, 0)) for k in ('x', 'y', 'width', 'height')]
            cell['pts'] = [(float(m.get('x')), float(m.get('y'))) for m in g.iter('mxPoint') if m.get('as') is None]
        cells[cell['id']] = cell
    return cells


def absolute(cells, c):
    x, y, w, h = c['geo']
    p = cells.get(c['parent'])
    while p is not None and 'geo' in p:
        x, y = x + p['geo'][0], y + p['geo'][1]
        p = cells.get(p['parent'])
    return x, y, w, h


def crosses(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


def hits(a, b, box):
    """Does the segment a-b pass through the box (shrunk a little)."""
    x, y, w, h = box
    x, y, w, h = x + 4, y + 4, w - 8, h - 8
    if w <= 0 or h <= 0:
        return False
    if x <= a[0] <= x + w and y <= a[1] <= y + h:
        return True
    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return any(crosses(a, b, corners[i], corners[(i + 1) % 4]) for i in range(4))


def is_icon(c):
    return 'image=' in c['style'] and not c['edge']


def is_zone(c):
    return not c['edge'] and 'geo' in c and not is_icon(c) and c['geo'][2] > 220 and c['geo'][3] > 140 and 'text;' not in c['style']


def score(cells):
    boxes = {i: absolute(cells, c) for i, c in cells.items() if 'geo' in c and not c['edge']}
    hard, soft = [], {}
    icons = [i for i, c in cells.items() if is_icon(c)]
    for n, a in enumerate(icons):
        for b in icons[n + 1:]:
            ax, ay, aw, ah = boxes[a]
            bx, by, bw, bh = boxes[b]
            if ax < bx + bw - 2 and bx < ax + aw - 2 and ay < by + bh - 2 and by < ay + ah - 2:
                hard.append(f'icons overlap: {a} / {b}')
    # edges as polylines between source and target centres
    lines = {}
    for i, c in cells.items():
        if not (c['edge'] and c['source'] in boxes and c['target'] in boxes):
            continue
        s_, t = boxes[c['source']], boxes[c['target']]
        pts = [(s_[0] + s_[2] / 2, s_[1] + s_[3] / 2)] + c['pts'] + [(t[0] + t[2] / 2, t[1] + t[3] / 2)]
        lines[i] = pts
    segs = {i: list(zip(p, p[1:])) for i, p in lines.items()}
    # A call between two shapes in one container stays in it: every waypoint inside the frame.
    for i, pts in lines.items():
        c = cells[i]
        sp, tp = cells[c['source']].get('parent'), cells[c['target']].get('parent')
        if sp == tp and sp in boxes and sp not in ('1', 'rg'):
            fx, fy, fw, fh = boxes[sp]
            if any(not (fx < x < fx + fw and fy < y < fy + fh) for x, y in pts):
                hard.append(f'edge {i} between two shapes in {sp} leaves it')
    cross = 0
    ids = list(segs)
    for n, a in enumerate(ids):
        for b in ids[n + 1:]:
            ca, cb = cells[a], cells[b]
            if {ca['source'], ca['target']} & {cb['source'], cb['target']}:
                continue
            cross += sum(crosses(p, q, r, s_) for p, q in segs[a] for r, s_ in segs[b])
    through = 0
    for i, ss in segs.items():
        ends = {cells[i]['source'], cells[i]['target']}
        for j in icons:
            if j in ends or cells[j]['parent'] in ends:
                continue
            if any(hits(p, q, boxes[j]) for p, q in ss):
                through += 1
    length = sum(((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2) ** 0.5 for ss in segs.values() for p, q in ss)
    leaves = [boxes[i] for i in icons]
    if leaves:
        x0, y0 = min(b[0] for b in boxes.values()), min(b[1] for b in boxes.values())
        x1, y1 = max(b[0] + b[2] for b in boxes.values()), max(b[1] + b[3] for b in boxes.values())
        W, H = x1 - x0, y1 - y0
        soft['aspect'] = max(W / H, H / W) if W and H else 1
    labels = 0
    for i, c in cells.items():
        if 'geo' in c and not c['edge'] and 'text;' in c['style'] and c['value']:
            plain = re.sub(r'<[^>]+>', '\n', c['value'])
            longest = max((len(l) for l in plain.splitlines()), default=0)
            if longest * 6.2 > c['geo'][2] + 40:
                labels += 1
    soft.update(crossings=cross, through_icons=through, label_overflow=labels, edge_len=length / max(len(segs), 1) / 100)
    total = cross * 3 + through * 5 + labels * 2 + max(soft.get('aspect', 1) - 1.8, 0) * 6 + soft['edge_len']
    return hard, soft, round(total, 1)


def run_one(spec, tmp, seed):
    import yaml
    path = os.path.join(tmp, f'spec-{seed}.yaml')
    out = os.path.join(tmp, f'd-{seed}.drawio')
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(spec, f, sort_keys=False, allow_unicode=True)
    try:
        p = subprocess.run([sys.executable, '-I', NEW, path, '--out', out], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return path, out, ['script hangs: no result after 60 s'], {}, 999
    if p.returncode != 0 or not os.path.isfile(out):
        return path, out, ['script failed: ' + (p.stdout + p.stderr).strip()[-300:]], {}, 999
    v = subprocess.run([sys.executable, '-I', VERIFY, path, out], capture_output=True, text=True)
    hard = [] if v.returncode == 0 else ['verify: ' + (v.stdout + v.stderr).strip()[-300:]]
    h, soft, total = score(read_cells(out))
    return path, out, hard + h, soft, total


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--n', type=int, default=50)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--keep-worst', type=int, default=5, help='copy the specs and diagrams of the worst N here')
    ap.add_argument('--out', default=None, help='directory for kept cases and report.json')
    ap.add_argument('--max-score', type=float, default=None, help='fail when the mean score is above')
    args = ap.parse_args()
    try:
        docs, blocks = load_pool()
    except ImportError:
        print('[skip] no YAML parser - pip install pyyaml')
        return 2

    results, failed = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for k in range(args.n):
            seed = args.seed * 100000 + k
            spec = generate(random.Random(seed), docs, blocks, seed)
            path, out, hard, soft, total = run_one(spec, tmp, seed)
            results.append({'seed': seed, 'score': total, 'hard': hard, 'soft': soft, 'spec': path, 'drawio': out})
            if hard:
                failed += 1
                print(f'[fail] seed {seed}: {hard[0][:200]}')
        ranked = sorted(results, key=lambda r: (bool(r['hard']), r['score']), reverse=True)
        if args.out:
            os.makedirs(args.out, exist_ok=True)
            for r in ranked[:args.keep_worst]:
                for key in ('spec', 'drawio'):
                    with open(r[key], 'rb') as src, open(os.path.join(args.out, os.path.basename(r[key])), 'wb') as dst:
                        dst.write(src.read())
            with open(os.path.join(args.out, 'report.json'), 'w', encoding='utf-8') as f:
                json.dump([{k: v for k, v in r.items() if k not in ('spec', 'drawio')} for r in ranked], f, indent=1)

    scores = [r['score'] for r in results if not r['hard']]
    mean = statistics.mean(scores) if scores else 0
    print(f'{len(results)} specs, {failed} hard failures, mean score {mean:.1f}, worst {ranked[0]["score"]} (seed {ranked[0]["seed"]})')
    for name in ('crossings', 'through_icons', 'label_overflow', 'aspect'):
        vals = [r['soft'].get(name, 0) for r in results if r['soft']]
        if vals:
            print(f'  {name:15} mean {statistics.mean(vals):6.2f}  max {max(vals):6.2f}')
    if failed or (args.max_score is not None and mean > args.max_score):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
