#!/usr/bin/env python3
"""Checks a diagram against the spec it was drawn from - the "check against the spec" step
of the iac-diagram skill, as a script.

    python3 verify_diagram.py ./infra-spec.yaml ./infra-diagram.drawio [--language de]

The second argument may also be the infra-diagram.drawio.png; the XML is read from it.

  - every key under `resources:` is drawn exactly once, and nothing else is drawn as a resource
  - the open entries are counted in the panel, and a resource one of them points at is drawn red
  - every `wiring.optional` resource is marked optional
  - with --language de: no ae/oe/ue/ss transliterations in the fixed labels ("ueber", "oeffentlich")

Exit 0 consistent, 1 a mismatch, 2 could not run.
"""

import argparse
import html
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drawio_png  # noqa: E402

# Drawn by the script although the spec may not list them: application insights next to the
# workspace, and the network and workspace when the deployment set only references them.
IMPLIED = {'application-insights', 'virtual-network', 'log-analytics-workspace'}
# Resources the script draws under a fixed id instead of res-<key>.
FIXED_IDS = {'virtual-network': 'vnet', 'log-analytics-workspace': 'law'}
TRANSLITERATED = re.compile(r'\b(ueber\w*|oeffentlich\w*|fuer|koennen|muessen|zurueck\w*|loesch\w*|aender\w*|vorhanden\s+-\s+wird\s+nicht\s+erstell\w*\s+fuer)\b', re.I)


def plain(text):
    text = re.sub(r'<[^>]+>', ' ', html.unescape(text or ''))
    return re.sub(r'\s+', ' ', html.unescape(text)).strip().lower()


def cells_of(path):
    cells = {}
    for model in drawio_png.graph_models(drawio_png.read_xml(path)):
        for c in ET.fromstring(model).iter('mxCell'):
            cells[c.get('id')] = {'value': c.get('value') or '', 'style': c.get('style') or ''}
    return cells


def verify(spec, cells, language):
    bad = []
    resources = list((spec.get('resources') or {}).keys())
    drawn = {k[4:] for k in cells if k.startswith('res-') and not k.endswith('-icon')}
    drawn |= {k for k, cid in FIXED_IDS.items() if cid in cells}
    for k in resources:
        if k not in drawn:
            bad.append(f"resource '{k}' is in the spec but not drawn")
    for k in sorted(drawn - set(resources) - IMPLIED):
        bad.append(f"'{k}' is drawn but not in the spec")

    open_entries = [o for o in (spec.get('open') or []) if isinstance(o, dict)]
    if open_entries:
        panel = ' '.join(plain(v['value']) for k, v in cells.items() if k.startswith('panel'))
        if not re.search(r"\b%d\b" % len(open_entries), panel):
            bad.append(f"the panel does not count the {len(open_entries)} open entries")
        for o in open_entries:
            key = str(o.get('key') or '')
            if key.startswith('resources.'):
                r = key.split('.')[1]
                c = cells.get(f"res-{r}")
                if c and '#D13438' not in c['style']:
                    bad.append(f"open entry on '{r}', but the resource is not drawn red")

    optional = (spec.get('wiring') or {}).get('optional') or []
    for k in optional:
        c = cells.get(f'res-{k}')
        if c and 'opacity=' not in c['style']:
            bad.append(f"optional resource '{k}' is not faded")

    if language == 'de':
        for cid, v in cells.items():
            m = TRANSLITERATED.search(plain(v['value']))
            if m:
                bad.append(f"{cid}: transliterated umlaut '{m.group(0)}' - write ä/ö/ü/ß")
    return bad


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')  # the messages carry umlauts; a Windows console is cp1252
    ap = argparse.ArgumentParser(description='Check a diagram against its infra-spec.yaml.')
    ap.add_argument('spec')
    ap.add_argument('diagram', help='the .drawio or the .drawio.png')
    ap.add_argument('--language', choices=['de', 'en'], default='en')
    args = ap.parse_args()
    try:
        import yaml
    except ImportError:
        print('[skip] no YAML parser - pip install pyyaml')
        return 2
    for p in (args.spec, args.diagram):
        if not os.path.isfile(p):
            print(f"[skip] {p} not found")
            return 2
    with open(args.spec, encoding='utf-8') as f:
        spec = yaml.safe_load(f) or {}
    bad = verify(spec, cells_of(args.diagram), args.language)
    for b in bad:
        print(f"[FAIL] {b}")
    if not bad:
        print(f"[ ok ] {args.diagram} matches {args.spec}")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
