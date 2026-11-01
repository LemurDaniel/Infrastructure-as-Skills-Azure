#!/usr/bin/env python3
"""Tests for new_diagram.py: fixture specs in, assertions on the generated .drawio out.

The plugin evals cannot cover the picture - the eval sandbox has no shell on Windows, so a
run can write a spec but not draw it. This is where the drawing is verified: every case
renders a spec and asserts what the picture has to say, which zones exist, how many lines
and in which colour, that private endpoints are one icon, that nothing leaks Python syntax
into a label.

    python3 run_diagram_tests.py            # every case
    python3 run_diagram_tests.py -k public  # cases whose name contains "public"

Needs PyYAML (new_diagram.py needs it). Exit 0 all passed, 1 a check failed, 2 could not run.
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'scripts', 'new_diagram.py')
FIXTURES = os.path.join(HERE, 'fixtures')

PRIVATE, PUBLIC = '#0078D4', '#D83B01'


def load(spec, language):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, 'd.drawio')
        proc = subprocess.run([sys.executable, '-I', SCRIPT, spec, '--language', language, '--out', out],
                              capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.isfile(out):
            return proc, None
        root = ET.parse(out).getroot()
    cells = {}
    for c in root.iter('mxCell'):
        if c.get('id') in ('0', '1'):
            continue
        cells[c.get('id')] = {'value': c.get('value') or '', 'style': c.get('style') or '', 'parent': c.get('parent'),
                              'edge': c.get('edge') == '1', 'source': c.get('source'), 'target': c.get('target')}
        g = c.find('mxGeometry')
        if g is not None:
            cells[c.get('id')]['geo'] = {k: float(g.get(k, 0)) for k in ('x', 'y', 'width', 'height')}
            # the waypoints only - a label offset is an mxPoint too (as="offset")
            cells[c.get('id')]['points'] = [(float(m.get('x')), float(m.get('y'))) for m in g.iter('mxPoint') if m.get('as') is None]
    return proc, cells


def vertices(cells):
    return {k: v for k, v in cells.items() if not v['edge']}


def edges(cells):
    return {k: v for k, v in cells.items() if v['edge']}


def styled(cell, token):
    return token in cell['style']


def is_box(cell):
    """A resource drawn as a box because its type has no icon."""
    return 'image;' not in cell['style'] and 'rounded=1' in cell['style'] and 'container=1' not in cell['style']


# --- checks that hold for every picture ------------------------------------------------
def generic(cells):
    bad = []
    for k, v in cells.items():
        for field in ('value',):
            if "{'" in v[field] or 'None' in v[field] or "['" in v[field]:
                bad.append(f"{k}: label leaks Python syntax: {v[field][:60]!r}")
    for k, v in vertices(cells).items():
        if 'container=1' in v['style'] and 'strokeColor=none' not in v['style']:   # the invisible outer cell of a split
            if 'rounded=1' not in v['style']:
                bad.append(f"{k}: container without rounded corners")
            if 'fillColor=none' in v['style'] or 'fillColor=' not in v['style']:
                bad.append(f"{k}: container without a solid fill")
    for k, v in edges(cells).items():
        if v['source'] not in cells or v['target'] not in cells:
            bad.append(f"{k}: edge with a missing end ({v['source']} -> {v['target']})")
        if 'strokeColor=' not in v['style']:
            bad.append(f"{k}: edge without a colour")
    # An arrowhead must stay readable: a line ending at an icon and a line leaving it never use
    # the same anchor point, or the two share a stub and one head hides the other.
    def anchor(style, kind):
        m = re.search(kind + r'X=([\d.]+);' + kind + r'Y=([\d.]+)', style)
        return (m.group(1), m.group(2)) if m else None
    for k in vertices(cells):
        ins = {anchor(e['style'], 'entry') for e in edges(cells).values() if e['target'] == k} - {None}
        outs = {anchor(e['style'], 'exit') for e in edges(cells).values() if e['source'] == k} - {None}
        if ins & outs:
            bad.append(f"{k}: an incoming and an outgoing line share the anchor {sorted(ins & outs)}")
    pe = [k for k in vertices(cells) if k.startswith('pe-') and k != 'pe-bundle']
    if pe:
        bad.append(f"one private endpoint icon per resource is back: {pe}")
    if not any(k == 'title' for k in cells):
        bad.append('no title')
    notice = cells.get('ai-notice')
    if not notice or not re.search(r'AI-generated|KI-generiert', notice['value']):
        bad.append('no AI notice')
    return bad


def count_colour(cells, colour):
    return sum(1 for v in edges(cells).values() if f'strokeColor={colour}' in v['style'])


# --- the cases ---------------------------------------------------------------------------
def case_ten_resources(cells):
    bad = []
    for need in ('z-ext', 'z-paas', 'z-monitoring', 'z-dnszones', 'pe-bundle', 'snet-pe', 'snet-c0', 'legend', 'subtitle', 'panel', 'law', 'dns'):
        if need not in cells:
            bad.append(f"missing {need}")
    res = [k for k in vertices(cells) if k.startswith('res-') and not k.endswith('-icon') and k != 'res-application-insights']
    if len(res) != 10:
        bad.append(f"expected 10 drawn resources, found {len(res)}: {sorted(res)}")
    if len(edges(cells)) != 10:
        bad.append(f"expected 10 lines (9 access; a role assignment is text on the target, not a line), found {len(edges(cells))}")
    if (count_colour(cells, PUBLIC), count_colour(cells, PRIVATE)) != (2, 8):
        bad.append(f"expected 2 orange (Entra, SharePoint) and 8 blue lines, found {count_colour(cells, PUBLIC)} and {count_colour(cells, PRIVATE)}")
    boxes = [k for k, v in vertices(cells).items() if k.startswith('res-') and is_box(v)]
    if boxes != ['res-event-grid']:
        bad.append(f"the one type without an icon should be the only box, found {boxes}")
    if 'event-grid' in cells.get('res-event-grid-icon', {}).get('value', '') and 'no question set' not in cells['res-event-grid-icon']['value']:
        bad.append('the box does not say it has no question set')
    if 'App Service: AcrPull' not in cells.get('res-container-registry', {}).get('value', ''):
        bad.append('the role is not on the target label')
    if 'opacity=' in cells.get('res-redis-cache', {}).get('style', '') or 'optional' in cells.get('res-redis-cache', {}).get('value', ''):
        bad.append('a resource of the spec is drawn faded or marked optional - it is built like any other')
    if 'public access disabled' not in cells.get('z-paas', {}).get('value', ''):
        bad.append('the PaaS zone does not say public access is disabled')
    if 'Diagnostics: existing, id open' not in cells.get('panel', {}).get('value', ''):
        bad.append('the panel does not say the referenced workspace exists with its id open')
    if cells.get('z-monitoring', {}).get('parent') != '1' or cells.get('z-dnszones', {}).get('parent') != '1':
        bad.append('referenced monitoring and DNS should sit outside the subscription')
    if 'snet-app-integration' not in cells.get('snet-c0', {}).get('value', '') or 'Microsoft.Web/serverFarms' not in cells.get('snet-c0', {}).get('value', ''):
        bad.append('the compute subnet is not named or does not carry its delegation')
    if 'virtual-network.' in cells.get('snet-c0', {}).get('value', '') or '10.40.2.0/26' not in cells.get('snet-c0', {}).get('value', ''):
        bad.append('a subnet reference was not shortened to its name, or lost its range')
    if len([k for k in cells if k.startswith('snet-c')]) != 1:
        bad.append('both compute resources should share the one integration subnet')
    if 'Webshop frontend' not in cells.get('res-app-service', {}).get('value', ''):
        bad.append('the purpose is not on the label')
    if 'No service is reachable' not in cells.get('subtitle', {}).get('value', ''):
        bad.append('the subtitle does not state the posture')
    if not any(k.startswith('act-') for k in cells) or 'act-users' not in cells or 'act-external-entra-id' not in cells:
        bad.append('actors missing from the external zone')
    return bad


def case_ten_resources_de(cells):
    bad = []
    if 'Architektur' not in cells.get('title', {}).get('value', ''):
        bad.append('title not in German')
    if 'ohne Fragenset' not in cells.get('res-event-grid-icon', {}).get('value', ''):
        bad.append('no-question-set note not in German')
    if 'Diagnose: vorhanden, ID offen' not in cells.get('panel', {}).get('value', ''):
        bad.append('the open workspace id is not said in German')
    return bad


def case_public_webshop(cells):
    bad = []
    for need in ('z-ext', 'act-internet', 'z-compute', 'z-paas', 'z-monitoring', 'legend'):
        if need not in cells:
            bad.append(f"missing {need}")
    for forbidden in ('vnet', 'pe-bundle', 'snet-pe', 'z-dnszones'):
        if forbidden in cells:
            bad.append(f"{forbidden} drawn although there is no network")
    if len(edges(cells)) != 3 or (count_colour(cells, PUBLIC), count_colour(cells, PRIVATE)) != (2, 1):
        bad.append(f"expected 3 lines (2 orange, 1 blue), found {len(edges(cells))} ({count_colour(cells, PUBLIC)} orange, {count_colour(cells, PRIVATE)} blue)")
    if any('redis' in k for k in cells):
        bad.append('an access target that is no resource in the spec was drawn')
    if cells.get('z-monitoring', {}).get('parent') != 'rg':
        bad.append('a workspace this deployment creates belongs inside the resource group')
    if 'reachable from the internet' not in cells.get('subtitle', {}).get('value', ''):
        bad.append('the subtitle does not state that the system is public')
    legend = cells.get('legend', {}).get('value', '')
    if 'private endpoint' not in legend or 'internet' not in legend:
        bad.append('the legend does not list both line colours')
    if 'no public access' in ''.join(v['value'] for v in cells.values()):
        bad.append('a public deployment is marked as having no public access')
    return bad


def case_corp_spoke_roles(cells):
    """Twenty resources, two of them twice: instance keys, a zone for what is not called, and
    lines told apart - one colour per caller, one row of services, no line through an icon."""
    bad = []
    for need in ('res-app-service__web', 'res-app-service__mcp', 'res-storage-account__host', 'z-support', 'z-paas', 'legend'):
        if need not in cells:
            bad.append(f"missing {need}")
    for k in cells:
        if k.startswith('res-user-assigned-identity') or k.startswith('res-network-security-group'):
            if cells[k]['parent'] != 'z-support':
                bad.append(f"{k} is a service zone resident, not part of the support zone")
    colours = set()
    for e in edges(cells).values():
        m = re.search(r'strokeColor=(#[0-9A-Fa-f]{6})', e['style'])
        if m and m.group(1) != PUBLIC:
            colours.add(m.group(1))
    if len(colours) < 4:
        bad.append(f"four callers should draw in four colours, found {sorted(colours)}")
    out_of_pe = [e for e in edges(cells).values() if e['source'] == 'pe-bundle']
    into_pe = [e for e in edges(cells).values() if e['target'] == 'pe-bundle']
    if len(out_of_pe) != 7 or len(into_pe) != 4:
        bad.append(f"hub layout: expected 4 callers into the endpoints and 7 services out of them, found {len(into_pe)} and {len(out_of_pe)}")
    if "container-apps" in cells['legend']['value'] or 'Container App' not in cells['legend']['value']:
        bad.append('the legend does not name the callers')
    if any(PRIVATE in e['style'] for e in into_pe):
        bad.append(f"a caller is drawn in {PRIVATE}, the colour of the line from the endpoints to the service")
    if 'Container App' in cells['pe-bundle']['value']:
        bad.append('the Container Apps environment is injected into its subnet and has no private endpoint, but the hub counts it')
    # The workspace leaves public access enabled: neither the subtitle nor the footer may claim otherwise.
    if 'Log Analytics' not in cells['subtitle']['value'] or 'Kein Dienst' in cells['subtitle']['value'] or 'No service' in cells['subtitle']['value']:
        bad.append('the subtitle claims no service is public although the workspace is')
    if 'Log Analytics' not in cells['rg-private']['value']:
        bad.append('the footer says "no public access" without naming the workspace as the exception')
    # Traffic out of the network to the monitoring zone is not drawn: the zone carries the diagnostics note.
    if any(e['target'] in ('res-application-insights', 'res-log-analytics-workspace') for e in edges(cells).values()):
        bad.append('a line leaves the network for the monitoring zone')
    return bad


def absolute(cells, cid):
    """x, y, w, h of a vertex in page coordinates (geometry is relative to the parent)."""
    c, x, y = cells[cid], 0.0, 0.0
    while c is not None and 'geo' in c:
        x, y = x + c['geo']['x'], y + c['geo']['y']
        c = cells.get(c['parent'])
    g = cells[cid]['geo']
    return x, y, g['width'], g['height']


def case_private_stages_open(cells):
    """A PaaS -> PaaS line (search reading storage, search calling the model) runs on a track of
    its own in the channel between the two service columns: it crosses no other icon and no label
    slot, and its label sits on its own run. Every role the spec assigns to a resource is on
    that resource's label with its principal."""
    import yaml
    bad = []
    spec = yaml.safe_load(open(os.path.join(FIXTURES, 'private-stages-open.yaml'), encoding='utf-8'))
    paas = [k for k, v in cells.items() if k.startswith('res-') and v.get('parent') == 'z-paas']
    pp = [e for e in edges(cells).values() if e['source'] in paas and e['target'] in paas]
    if len(pp) != 2:
        bad.append(f"expected the two PaaS-to-PaaS lines (indexer, embeddings), found {len(pp)}")
    slots = {}
    for k in paas:
        x, y, w, h = absolute(cells, k)
        slots[k] = (x + w / 2 - 86, x + w / 2 + 86)   # the slot: SLOT_W 172 around the icon
    for e in pp:
        pts = e['points']
        sx, sy, sw, sh = absolute(cells, e['source'])
        tx, ty, tw, th = absolute(cells, e['target'])
        # the anchors come from the style: two lines on one side take different heights
        anchor = lambda key, default: float((re.search(key + r'=([\d.]+)', e['style']) or [None, default])[1])
        src = (sx + sw * anchor('exitX', 1), sy + sh * anchor('exitY', 0.5))
        dst = (tx + tw * anchor('entryX', 1), ty + th * anchor('entryY', 0.5))
        path = [src] + pts + [dst]
        for (x1, y1), (x2, y2) in zip(path, path[1:]):
            for k in paas:
                if k in (e['source'], e['target']) and y1 == y2:
                    continue
                ix, iy, iw, ih = absolute(cells, k)
                lo_y, hi_y = min(y1, y2), max(y1, y2)
                below = [absolute(cells, o)[1] for o in paas if absolute(cells, o)[1] > iy]
                slot_bottom = min(below) if below else iy + ih + 80   # the slot ends where the next icon starts
                lo_x, hi_x = min(x1, x2), max(x1, x2)
                # the icon box, and the slot below it that holds the label and the roles
                if lo_x < slots[k][1] and hi_x > slots[k][0] and lo_y < slot_bottom and hi_y > iy:
                    if k in (e['source'], e['target']) and x1 == x2 and (x1 > slots[k][1] or x1 < slots[k][0]):
                        continue
                    bad.append(f"line {e['source']} -> {e['target']} crosses {k}")
        if not (len(pts) == 2 and pts[0][0] == pts[1][0] and all(not (lo < pts[0][0] < hi) for lo, hi in slots.values())):
            bad.append(f"line {e['source']} -> {e['target']} is not on a vertical track outside every icon slot")
        if not e['value']:
            bad.append(f"line {e['source']} -> {e['target']} lost its label")
    for key, node in spec['resources'].items():
        ras = (node.get('identity') or {}).get('role_assignments')
        ras = ras.get('value') if isinstance(ras, dict) else None
        if isinstance(ras, dict):
            ras = ras.get('production') or next(iter(ras.values()))
        for ra in ras or []:
            label = ' '.join(v['value'] for k, v in cells.items() if k in (f'res-{key}', f'res-{key}-icon'))
            # the principal is named as the picture names it (kind title · instance), the role verbatim
            if f": {ra['role']}" not in label:
                bad.append(f"{key}: role '{ra['principal']}: {ra['role']}' is not on the label")
    return bad


FOLDER = 'azure2/general/Resource_Groups.svg'   # Azure's resource group icon, inline in a label


def label_of(cells, *ids):
    return ' '.join(cells[i]['value'] for i in ids if i in cells)


def inside(cells, child, frame):
    """The child's box lies within the frame's box."""
    cx, cy, cw, ch = absolute(cells, child)
    fx, fy, fw, fh = absolute(cells, frame)
    return fx <= cx and cy >= fy and cx + cw <= fx + fw and cy + ch <= fy + fh


def case_resource_groups_split(cells):
    """With a split the services stand group by group, each group in a frame of its colour: solid
    when the group is created, dashed when it exists. Five services in two groups (data and
    application) give the side layout. A framed resource carries no tag (the frame says it), compute in the subnets does; the
    network is the network group's frame, the support zone has a frame per group, the monitoring
    zone's title names its group, and nothing is framed around everything."""
    bad = []
    outer = cells.get('rg', {}).get('value', '')
    if 'rg-shop-prod-we' in outer or 'Resource groups' in outer or 'Deployment' in outer:
        bad.append(f"the outer cell names a group or says deployment: {outer[:80]!r}")
    if 'strokeColor=none' not in cells.get('rg', {}).get('style', ''):
        bad.append("a frame is drawn around everything with a split")
    if 'rg-icon' in cells:
        bad.append("the outer frame carries the resource group icon - the deployment would be mistaken for a group")
    for frame, tag, dashed in (('rg-data', 'data (created)', False), ('rg-application', 'application (created)', False),
                               ('rg-network-support', 'network (existing)', True), ('rg-security-support', 'security (created)', False)):
        c = cells.get(frame)
        if c is None:
            bad.append(f"no frame {frame}")
            continue
        if FOLDER not in c['value'] or tag not in c['value']:
            bad.append(f"{frame} does not say '{tag}': {c['value']!r}")
        if ('dashed=1' in c['style']) != dashed:
            bad.append(f"{frame} is {'dashed' if 'dashed=1' in c['style'] else 'solid'}, a group that is {tag.split('(')[1][:-1]}")
    for res, frame in (('storage-account', 'rg-data'), ('cosmos-db', 'rg-data'), ('key-vault', 'rg-data'),   # key-vault: placement departs
                       ('container-registry', 'rg-application'), ('search-service', 'rg-application')):
        c = cells.get(f'res-{res}')
        if c is None:
            bad.append(f"{res} is not drawn")
            continue
        if c['parent'] != frame or not inside(cells, f'res-{res}', frame):
            bad.append(f"{res} is not inside {frame} (parent {c['parent']})")
        if FOLDER in label_of(cells, f'res-{res}', f'res-{res}-icon'):
            bad.append(f"{res} repeats its group as a tag inside the frame that names it")
    for res, frame in (('network-security-group', 'rg-network-support'), ('user-assigned-identity', 'rg-security-support')):
        if cells.get(f'res-{res}', {}).get('parent') != frame:
            bad.append(f"{res} is not in {frame}")
    if FOLDER not in label_of(cells, 'res-app-service', 'res-app-service-icon') or 'application (created)' not in label_of(cells, 'res-app-service', 'res-app-service-icon'):
        bad.append("compute is not tagged 'application (created)'")
    vnet = cells.get('vnet', {})
    if 'network (existing)' not in vnet.get('value', '') or 'dashed=1' not in vnet.get('style', ''):
        bad.append(f"the network is not the dashed frame of its existing group: {vnet.get('value', '')!r}")
    if 'monitoring (created)' not in cells.get('z-monitoring', {}).get('value', ''):
        bad.append(f"the monitoring zone's title does not name its group: {cells.get('z-monitoring', {}).get('value', '')!r}")
    for part in ('Resource groups:', 'application (created)', 'network (existing)', 'data (created)', 'monitoring (created)'):
        if part not in ' '.join(v['value'] for k, v in cells.items() if k.startswith('panel')):
            bad.append(f"the decisions panel lacks '{part}'")
    legend = cells.get('legend', {}).get('value', '')
    if 'Resource groups' not in legend or 'data (created)' not in legend:
        bad.append('the legend does not list the groups')
    if FOLDER in label_of(cells, 'pe-bundle'):
        bad.append('the private endpoints carry a group - they live with the resource they serve')
    return bad


def case_resource_groups_small(cells):
    """The compact layout: three services in three groups stand side by side in one row, each in
    its frame, and every service sits inside its own."""
    bad = []
    want = {'rg-security': 'key-vault', 'rg-data': 'storage-account', 'rg-application': 'container-registry'}
    ys = set()
    for frame, res in want.items():
        c = cells.get(frame)
        if c is None:
            bad.append(f"no frame {frame}")
            continue
        if not inside(cells, f'res-{res}', frame) or cells[f'res-{res}']['parent'] != frame:
            bad.append(f"{res} is not inside {frame}")
        ys.add(round(absolute(cells, frame)[1]))
    if len(ys) > 1:
        bad.append(f"the frames do not stand in one row: tops {sorted(ys)}")
    xs = sorted((absolute(cells, f)[0], absolute(cells, f)[0] + absolute(cells, f)[2]) for f in want if f in cells)
    for (x1, e1), (x2, e2) in zip(xs, xs[1:]):
        if x2 < e1:
            bad.append('two frames overlap')
    if 'dashed=1' not in cells.get('rg-data', {}).get('style', ''):
        bad.append("rg-data (existing) is not dashed")
    return bad


def case_no_split_no_group_tags(cells):
    """One group, no split: nothing is tagged and the frame keeps the group's own name."""
    bad = [f"{k}: carries a group tag without a split" for k, v in cells.items() if FOLDER in v['value']]
    if 'rg-icon' in cells:
        bad.append('a frame with a resource group icon is back')
    if 'rg-shop-prod-we' not in cells.get('rg', {}).get('value', ''):
        bad.append('the resource group name is gone from the top line')
    if 'Resource groups' in ' '.join(v['value'] for v in cells.values()):
        bad.append('a panel line about resource groups is drawn without a split')
    return bad


def case_entry_chain(cells):
    """Front Door stands with the actors, the gateway and API Management in their subnets in the
    order a request meets them, the containers are words on the account (no box of their own),
    the topic's delivery into the function is a word on its label and no line, and what is
    reachable from the internet by what it is carries the warning."""
    bad = []
    if not cells['res-front-door']['parent'].startswith('z-act'):
        bad.append('front-door is not in a zone of its own left of the network')
    if cells['act-users']['parent'] == cells['res-front-door']['parent']:
        bad.append('the users and Front Door share a zone')
    if 'z-top-0' not in cells or not inside(cells, 'act-external-entra-id', 'z-top-0'):
        bad.append('the directory is not in a zone above the network')
    if 'strokeColor=none' not in cells.get('rg', {}).get('style', ''):
        bad.append('a frame is drawn around everything')
    for res, sn in (('application-gateway', 'snet-gateway'), ('api-management', 'snet-apim'), ('function-app', 'snet-func')):
        frame = next((k for k, v in cells.items() if k.startswith('snet-c') and sn in v['value']), None)
        if frame is None or not inside(cells, f'res-{res}', frame):
            bad.append(f"{res} is not in {sn}")
    pos = [absolute(cells, f'res-{r}') for r in ('application-gateway', 'api-management', 'function-app')]
    if [p[0] for p in pos] != sorted(p[0] for p in pos):
        bad.append(f"the subnets are not left to right in the order of the request: {[p[0] for p in pos]}")
    if len({round(p[1]) for p in pos}) > 1:
        bad.append(f"the chain is not one row: {[p[1] for p in pos]}")
    call = [e for e in edges(cells).values() if e['target'] == 'res-storage-account' and e['source'].startswith('snet-c')]
    if len(call) != 1 or len(call[0]['points']) != 2:
        bad.append('the call from the function into the storage account is not one line out of its subnet along a lane')
    for kind, n in (('network-security-group', 3), ('user-assigned-identity', 2)):
        b = f'res-bundle.{kind}.main'
        if b not in cells or f'{n}× ' not in label_of(cells, b):
            bad.append(f'the {n} {kind} resources are not one bundle icon')
    if any(k.startswith(('res-network-security-group__', 'res-user-assigned-identity__')) for k in cells):
        bad.append('a security group or identity has an icon of its own beside the bundle')
    for e in edges(cells).values():
        if e['source'] == 'res-application-gateway' and e['target'] == 'res-api-management' and e['points']:
            bad.append('the line between two neighbours in the chain is not straight')
    if 'res-blob-container' in cells:
        bad.append('the blob container has a box of its own')
    if 'order-documents' not in label_of(cells, 'res-storage-account'):
        bad.append('the container names are not on the storage account')
    for res in ('front-door', 'application-gateway', 'function-app'):
        if 'aus dem Internet erreichbar' not in label_of(cells, f'res-{res}'):
            bad.append(f"{res} is not marked as reachable from the internet")
    if 'pe-bundle' in cells and any(r in label_of(cells, 'pe-bundle') for r in ('Gateway', 'API Management')):
        bad.append('the gateway or API Management got a private endpoint')
    if any(e['source'] == 'res-event-grid-topic' and e['target'] == 'res-function-app' for e in edges(cells).values()):
        bad.append('the delivery into the function is a line again')
    if 'Event Grid Topic' not in label_of(cells, 'res-function-app'):
        bad.append('the delivery is not on the function label')
    for src_, dst_ in (('act-users', 'res-front-door'), ('res-front-door', 'res-application-gateway'), ('res-api-management', 'act-external-entra-id')):
        e = [e for e in edges(cells).values() if e['source'] == src_ and e['target'] == dst_]
        if not e:
            bad.append(f'no line {src_} -> {dst_}')
        elif e[0]['points']:
            bad.append(f'the line {src_} -> {dst_} is not one straight stretch')
    return bad


def case_dns_open(cells):
    """Private endpoints and no answer on who owns the zones: the zones are drawn anyway, red,
    marked open - not left out as if no name resolution were needed."""
    bad = []
    if 'dns' not in cells:
        return ['the private DNS zones are not drawn although private endpoints exist']
    if 'D13438' not in cells['dns']['style'] and 'D13438' not in cells['dns']['value']:
        bad.append('the open zones are not red')
    if 'offen' not in cells['dns']['value']:
        bad.append('the zones do not say they are open')
    return bad


def case_four_apps_one_subnet(cells):
    """Four apps in one subnet that call each other: they stand in a column, not a row (a row
    sends the first one's lines through the others), and a call between two of them never
    leaves the subnet - every waypoint lies inside its frame, the line is not drawn around it."""
    bad = []
    apps = [k for k in cells if k.startswith('res-app-service__')]
    if len(apps) != 4:
        return [f'expected four apps, found {len(apps)}']
    frames = {cells[a]['parent'] for a in apps}
    if len(frames) != 1:
        return [f'the apps do not share one subnet: {frames}']
    frame = frames.pop()
    if len({round(absolute(cells, a)[1]) for a in apps}) != 4:
        bad.append('the apps are not in a column (one row each)')
    fx, fy, fw, fh = absolute(cells, frame)
    n = 0
    for k, e in edges(cells).items():
        if e['source'] in apps and e['target'] in apps:
            n += 1
            for x, y in e['points']:
                if not (fx < x < fx + fw and fy < y < fy + fh):
                    bad.append(f"{k}: a call inside the subnet leaves it at ({x:.0f}, {y:.0f}), frame x {fx:.0f}-{fx + fw:.0f}")
    if n != 3:
        bad.append(f'expected three calls between the apps, found {n}')
    return bad


CASES = [
    ('ten-resources', os.path.join(FIXTURES, 'ten-resources.yaml'), 'en', case_ten_resources),
    ('ten-resources-de', os.path.join(FIXTURES, 'ten-resources.yaml'), 'de', case_ten_resources_de),
    ('public-webshop', os.path.join(FIXTURES, 'public-webshop.yaml'), 'en', case_public_webshop),
    ('corp-spoke-roles', os.path.join(FIXTURES, 'corp-spoke-roles.yaml'), 'en', case_corp_spoke_roles),
    ('private-stages-open', os.path.join(FIXTURES, 'private-stages-open.yaml'), 'de', case_private_stages_open),
    ('resource-groups-split', os.path.join(FIXTURES, 'resource-groups-split.yaml'), 'en', case_resource_groups_split),
    ('resource-groups-small', os.path.join(FIXTURES, 'resource-groups-small.yaml'), 'de', case_resource_groups_small),
    ('dns-open', os.path.join(FIXTURES, 'dns-open.yaml'), 'de', case_dns_open),
    ('entry-chain', os.path.join(FIXTURES, 'entry-chain.yaml'), 'de', case_entry_chain),
    ('four-apps-one-subnet', os.path.join(FIXTURES, 'four-apps-one-subnet.yaml'), 'en', case_four_apps_one_subnet),
    ('no-split-no-group-tags', os.path.join(FIXTURES, 'public-webshop.yaml'), 'en', case_no_split_no_group_tags),
]


def main():
    ap = argparse.ArgumentParser(description='Render fixture specs and assert on the drawing.')
    ap.add_argument('-k', help='only cases whose name contains this')
    args = ap.parse_args()
    try:
        import yaml  # noqa: F401
    except ImportError:
        print('[skip] no YAML parser - pip install pyyaml')
        return 2

    failed = 0
    for name, spec, language, check in CASES:
        if args.k and args.k not in name:
            continue
        if not os.path.isfile(spec):
            print(f"[skip] {name}: {spec} not found")
            return 2
        proc, cells = load(spec, language)
        if cells is None:
            print(f"[FAIL] {name}: new_diagram.py exited {proc.returncode}\n{proc.stdout}{proc.stderr}")
            failed += 1
            continue
        problems = generic(cells) + check(cells)
        if problems:
            failed += 1
            print(f"[FAIL] {name}")
            for p in problems:
                print(f"         - {p}")
        else:
            print(f"[ ok ] {name} - {len(vertices(cells))} shapes, {len(edges(cells))} lines")
    print('-' * 70)
    print(f"{failed} case(s) failed." if failed else 'All diagram cases passed.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
