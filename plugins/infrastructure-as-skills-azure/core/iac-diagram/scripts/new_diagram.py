#!/usr/bin/env python3
"""Draws an infra-spec.yaml as infra-diagram.drawio, with a computed layout.

The layout is calculated, not hand-placed: every icon gets a fixed slot on a
grid, containers are sized from their contents, and edges leave and enter at
fixed sides. Two runs on the same spec produce the same file, and nothing
overlaps by construction. The script still checks for overlaps afterwards and
fails if it finds one - a layout rule that stopped holding is a bug here, not
something to fix by hand in draw.io.

The picture is about who can reach what, drawn in zones:

  external zone | resource group > [ virtual network (subnets with their compute) | Azure PaaS
                                     identities, monitoring, name resolution below them ]
  legend and decisions below the group

The picture grows downwards, not sideways: nothing stands right of the services, so a
deployment of a dozen resources still fits an A4 page in landscape without shrinking.

Compute sits in the subnet it integrates with. Every private endpoint of the
deployment is one bundled icon in the endpoint subnet - one per resource drew a
column nobody could read. PaaS services sit in their own zone below the network,
because a PaaS service is not in the VNet, its endpoint is. The lines are access:
wiring.access (who calls whom), plus a line per role assignment, plus the
internet when the deployment is public. Diagnostics are one note in the
monitoring zone, not a line per resource. Referenced (existing) things are grey
and dashed; wiring.optional marks optional parts faded; wiring.purposes puts
what a resource is for on its label.

Needs PyYAML (pip install pyyaml). Without it the script exits 2.

Usage:
    python3 new_diagram.py ./infra-spec.yaml [--language de] [--out ./infra-diagram.drawio]

The language is `context.language` of the spec; --language overrides it.

Exit 0 written, 1 layout check failed or spec unreadable, 2 could not run.
"""

import argparse
import glob
import math
import os
import re
import sys
from xml.sax.saxutils import escape as _xml_escape

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_RESOURCES = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'resources'))

COLORS = {'green': '32', 'red': '31', 'yellow': '33'}
USE_COLOR = sys.stdout.isatty() and not os.environ.get('NO_COLOR')


def say(text, color=None):
    if color and USE_COLOR:
        print(f"\033[{COLORS[color]}m{text}\033[0m")
    else:
        print(text)


def esc(s):
    """XML-escape like .NET's SecurityElement.Escape: & < > " and '."""
    return _xml_escape('' if s is None else str(s), {'"': '&quot;', "'": '&apos;'})


def num(v):
    """Geometry values: integral floats print without a decimal part."""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def s(v):
    """PowerShell-style string interpolation: None is the empty string."""
    return '' if v is None else str(v)


LABELS = {
    'en': {
        'internet': 'Internet', 'users': 'Users', 'noPublic': 'no public access', 'existing': 'existing - not created',
        'decisions': 'Decisions', 'open': 'Open', 'assumed': 'Assumed', 'exposure': 'Exposure',
        'network': 'Network', 'mandates': 'Mandates', 'dns': 'Private DNS', 'diag': 'Diagnostics',
        'peSubnet': 'private endpoints', 'owner': 'owner', 'noSet': 'no question set',
        'arch': 'Architecture', 'ext': 'Internet and external services', 'monitoring': 'Monitoring',
        'diagNote': 'Diagnostic settings of all resources', 'nameRes': 'Name resolution',
        'peBundle': 'Private Endpoints', 'paas': 'Azure PaaS', 'paasPrivate': 'public access disabled', 'support': 'Identities and network baseline',
        'compute': 'Compute', 'computeSubnet': 'snet-compute', 'delegated': 'delegated to', 'optional': 'optional',
        'legend': 'Legend', 'legCallers': 'a caller on its way to the private endpoints - one colour per caller', 'legPE': 'from the private endpoints to the service, no public path', 'legPrivateAny': 'private access, no public path', 'legPrivate': 'access over a private endpoint, no public path',
        'legPublic': 'access from or over the internet', 'legExisting': 'existing, not created here',
        'legOptional': 'optional component', 'legOpen': 'open or assumed decision',
        'subPrivate': 'No service is reachable from the internet: access runs over private endpoints.',
        'subExc': 'Private by default; the named exceptions are reachable from the internet behind a firewall.',
        'subPublic': 'The system is reachable from the internet by design.',
        'subPrivateExc': 'Access runs over private endpoints; reachable from the internet: {names}.',
        'noPublicExc': 'no public access, except: {names}',
        'telemetry': 'telemetry', 'openRef': 'details in infra-decisions.md', 'noOwner': 'no owner yet',
        'rg': 'resource group', 'publicMark': 'reachable from the internet',
        'keyless': ' Access to the resources is by identity, no keys.',
    },
    'de': {
        'internet': 'Internet', 'users': 'Benutzer', 'noPublic': 'kein öffentlicher Zugriff', 'existing': 'vorhanden - wird nicht erstellt',
        'decisions': 'Entscheidungen', 'open': 'Offen', 'assumed': 'Angenommen', 'exposure': 'Erreichbarkeit',
        'network': 'Netzwerk', 'mandates': 'Vorgaben', 'dns': 'Private DNS', 'diag': 'Diagnose',
        'peSubnet': 'Private Endpoints', 'owner': 'zuständig', 'noSet': 'ohne Fragenset',
        'arch': 'Architektur', 'ext': 'Internet und externe Dienste', 'monitoring': 'Monitoring',
        'diagNote': 'Diagnose-Einstellungen aller Ressourcen', 'nameRes': 'Namensauflösung',
        'peBundle': 'Private Endpoints', 'paas': 'Azure PaaS', 'paasPrivate': 'öffentlicher Zugriff deaktiviert', 'support': 'Identitäten und Netzwerkgrundlage',
        'compute': 'Compute', 'computeSubnet': 'snet-compute', 'delegated': 'delegiert an', 'optional': 'optional',
        'legend': 'Legende', 'legCallers': 'Aufrufer auf dem Weg zu den Private Endpoints - eine Farbe je Aufrufer', 'legPE': 'von den Private Endpoints zum Dienst, kein öffentlicher Weg', 'legPrivateAny': 'privater Zugriff, kein öffentlicher Weg', 'legPrivate': 'Zugriff über Private Endpoint, kein öffentlicher Weg',
        'legPublic': 'Zugriff aus dem oder über das Internet', 'legExisting': 'vorhanden, wird hier nicht erstellt',
        'legOptional': 'optionales Bauteil', 'legOpen': 'offene oder angenommene Entscheidung',
        'subPrivate': 'Kein Dienst ist aus dem Internet erreichbar: Zugriffe laufen über Private Endpoints.',
        'subExc': 'Standardmäßig privat; die benannten Ausnahmen sind hinter einer Firewall aus dem Internet erreichbar.',
        'subPublic': 'Das System ist absichtlich aus dem Internet erreichbar.',
        'subPrivateExc': 'Zugriffe laufen über Private Endpoints; aus dem Internet erreichbar: {names}.',
        'noPublicExc': 'kein öffentlicher Zugriff, außer: {names}',
        'telemetry': 'Telemetrie', 'openRef': 'Details in infra-decisions.md', 'noOwner': 'noch ohne Zuständigen',
        'rg': 'Ressourcengruppe', 'publicMark': 'aus dem Internet erreichbar',
        'keyless': ' Zugriffe auf die Ressourcen laufen über Identitäten, ohne Schlüssel.',
    },
}

# Paths verified against draw.io's azure2 library - a wrong path exports as a
# broken-image placeholder, silently. A resource without a row is drawn as a box.
ICONS = {
    'resource-group': 'img/lib/azure2/general/Resource_Groups.svg',
    'storage-account': 'img/lib/azure2/storage/Storage_Accounts.svg',
    'virtual-network': 'img/lib/azure2/networking/Virtual_Networks.svg',
    'private-endpoint': 'img/lib/azure2/networking/Private_Endpoint.svg',
    'private-dns-zone': 'img/lib/azure2/networking/DNS_Zones.svg',
    'log-analytics-workspace': 'img/lib/azure2/analytics/Log_Analytics_Workspaces.svg',
    'key-vault': 'img/lib/azure2/security/Key_Vaults.svg',
    'app-service': 'img/lib/azure2/app_services/App_Services.svg',
    'function-app': 'img/lib/azure2/compute/Function_Apps.svg',
    'container-registry': 'img/lib/azure2/containers/Container_Registries.svg',
    'cosmos-db': 'img/lib/azure2/databases/Azure_Cosmos_DB.svg',
    'sql-server': 'img/lib/azure2/databases/SQL_Server.svg',
    'redis-cache': 'img/lib/azure2/databases/Cache_Redis.svg',
    'service-bus': 'img/lib/azure2/integration/Service_Bus.svg',
    'application-insights': 'img/lib/azure2/devops/Application_Insights.svg',
    # draw.io's library has no icon of its own for AI Foundry or Container Apps: the nearest ones.
    'foundry': 'img/lib/azure2/ai_machine_learning/Cognitive_Services.svg',
    'search-service': 'img/lib/azure2/app_services/Search_Services.svg',
    'container-apps': 'img/lib/azure2/containers/Container_Instances.svg',
    'user-assigned-identity': 'img/lib/azure2/identity/Managed_Identities.svg',
    'network-security-group': 'img/lib/azure2/networking/Network_Security_Groups.svg',
    'users': 'img/lib/azure2/identity/Users.svg',
    'entra-id': 'img/lib/azure2/identity/Azure_Active_Directory.svg',
}
TYPE_NAMES = {
    'storage-account': 'Storage Account', 'virtual-network': 'Virtual Network',
    'log-analytics-workspace': 'Log Analytics Workspace', 'key-vault': 'Key Vault',
    'app-service': 'App Service', 'function-app': 'Function App', 'container-registry': 'Container Registry',
    'cosmos-db': 'Cosmos DB', 'sql-server': 'SQL Server', 'redis-cache': 'Redis Cache', 'service-bus': 'Service Bus',
    'application-insights': 'Application Insights',
    'foundry': 'AI Foundry', 'search-service': 'AI Search', 'container-apps': 'Container App',
    'user-assigned-identity': 'Managed Identity', 'network-security-group': 'Network Security Group',
}

ACTOR_TITLES = {'entra-id': 'Entra ID', 'sharepoint-online': 'SharePoint Online', 'm365': 'Microsoft 365',
                'azure-devops': 'Azure DevOps', 'github': 'GitHub'}

# Compute is what runs code and integrates with a subnet; monitoring is what receives
# the logs; everything else that is not the network is PaaS, reached through an endpoint.
COMPUTE_KINDS = {'app-service', 'function-app', 'container-app', 'container-apps', 'container-apps-environment', 'virtual-machine', 'aks'}
MONITOR_KINDS = {'log-analytics-workspace', 'application-insights'}
# Not services that are called: identities hold roles, security groups guard subnets. They get a
# zone of their own so that no line to a service runs through them.
SUPPORT_KINDS = {'user-assigned-identity', 'network-security-group'}
DELEGATIONS = {'app-service': 'Microsoft.Web/serverFarms', 'function-app': 'Microsoft.Web/serverFarms',
               'container-apps-environment': 'Microsoft.App/environments', 'container-apps': 'Microsoft.App/environments'}


def base(key):
    """A second resource of one kind is `<set>__<instance>` in the spec (spec.md, "Several of a
    kind"); everything that looks a kind up - icon, title, question set - reads the set."""
    return key.partition('__')[0]

# A slot holds an icon and up to four label lines below it. The label is given
# the slot's width via labelWidth - without it draw.io wraps the label to the
# 48px image and breaks after every word.
SLOT_W, SLOT_H, ICON = 172, 132, 48
LABEL_W = SLOT_W - 10
HEAD, ZHEAD, PAD = 40, 30, 16
ZONE_W = SLOT_W + 40
TRK = 24   # spacing of parallel tracks
TOP = 80

CONTAINER_STYLE = 'rounded=1;arcSize=2;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#0078D4;verticalAlign=top;align=left;spacingLeft=36;spacingTop=4;fontStyle=1;container=1;collapsible=0;'
EXISTING_STYLE = 'dashed=1;strokeColor=#999999;fontColor=#777777;'
SUBNET_STYLE = 'rounded=1;arcSize=4;whiteSpace=wrap;html=1;fillColor=#F3F9FD;strokeColor=#7FBAEA;verticalAlign=top;align=left;spacingLeft=10;spacingTop=2;container=1;collapsible=0;'
EDGE_BASE = 'edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;strokeWidth=2;'
PRIVATE_COLOR, PUBLIC_COLOR = '#0078D4', '#D83B01'
# With three or more callers the private lines are told apart by colour: one colour per caller,
# a legend entry each. Orange stays what leaves or crosses the internet.
# Never blue (PRIVATE_COLOR, the line from the endpoints to the service), orange or red.
CALLER_COLORS = ['#008272', '#8764B8', '#498205', '#B146C2', '#8E562E', '#005B70', '#986F0B', '#69797E']


def zone_style(fill, stroke, font):
    return (f"rounded=1;arcSize=2;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontColor={font};"
            "verticalAlign=top;align=left;spacingLeft=12;spacingTop=6;fontStyle=1;container=1;collapsible=0;")


ZONES = {
    'external': zone_style('#FBF3EA', '#C19C77', '#8A5A2B'),
    'paas': zone_style('#F7F7F7', '#8A8886', '#323130'),
    # the zone lines arrive in: its title is at the bottom, out of their way
    'paas_in': zone_style('#F7F7F7', '#8A8886', '#323130').replace('verticalAlign=top', 'verticalAlign=bottom').replace('spacingTop=6', 'spacingBottom=4'),
    'platform': zone_style('#F5F0FA', '#8661C5', '#5C2D91'),
    'monitoring': zone_style('#F1F8F2', '#5BA55B', '#107C10'),
    'compute': zone_style('#F3F9FD', '#0078D4', '#005A9E'),
}


def get_at(m, keys):
    cur = m
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


STAGES = {'development', 'test', 'qa', 'uat', 'integration', 'staging', 'preproduction',
          'production', 'sandbox', 'demo', 'hotfix'}


# A per-stage value is a map keyed by stage. The page draws one picture, so it shows
# the value every stage shares, else production's, else the first stage's - printing
# the map itself leaks Python's dict syntax into the labels.
def collapse_stages(v):
    if isinstance(v, dict) and v and set(v) <= STAGES:
        vals = list(v.values())
        if all(x == vals[0] for x in vals):
            return vals[0]
        return v.get('production', vals[0])
    return v


# A decision is either { value, source } or a bare value.
def get_value(node):
    if isinstance(node, dict) and 'value' in node:
        return collapse_stages(node['value'])
    return collapse_stages(node)


def get_decision(m, keys):
    return get_value(get_at(m, keys))


# A referenced resource is recorded as "name / resource-group", or as a map with
# name and resource_group_name. The name goes on the shape; the group goes to
# the panel, where text has room. Putting both on an icon label overflows its
# fixed slot.
def split_ref(value):
    if value is None:
        return {'name': None, 'rg': None}
    if isinstance(value, dict):
        return {'name': value.get('name'), 'rg': value.get('resource_group_name') or value.get('resource_group')}
    parts = re.split(r'\s*/\s*', str(value), maxsplit=1)
    return {'name': parts[0], 'rg': parts[1] if len(parts) > 1 else None}


def subnet_name(value, resource_keys=()):
    """A subnet is named by what the spec calls it, and a reference may carry the resource's
    key in front (`virtual-network.snet-app`); the picture shows the name alone."""
    name = split_ref(value)['name']
    if name and '.' in name and name.split('.', 1)[0] in resource_keys:
        return name.split('.', 1)[1]
    return name


def as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def plain_len(html):
    return len(re.sub(r'<[^>]+>', '', html))


def format_label(title, sub, note):
    label = f"<b>{esc(title)}</b>"
    if sub:
        label += f"<br><font style='font-size:10px'>{esc(sub)}</font>"
    if note:
        label += f"<br><font style='font-size:10px'><i>{esc(note)}</i></font>"
    return label


def label_lines(label):
    return sum(max(1, math.ceil(plain_len(part) / 26)) for part in label.split('<br>'))


def icon_style(img, flagged, existing):
    style = f"image;aspect=fixed;html=1;points=[];align=center;verticalLabelPosition=bottom;verticalAlign=top;whiteSpace=wrap;labelBackgroundColor=none;labelWidth={LABEL_W};image={img};"
    if existing:
        style += 'opacity=60;fontColor=#777777;'
    if flagged:
        style += 'fontColor=#D13438;'
    return style


def has_question_set(key):
    return bool(glob.glob(os.path.join(PLUGIN_RESOURCES, '*', key, 'questions.yaml')))


def pitch_of(label):
    return max(92, 8 + ICON + 4 + 16 * label_lines(label) + 4)


def main():
    ap = argparse.ArgumentParser(description='Draw an infra-spec.yaml as a draw.io diagram.')
    ap.add_argument('path', help='the infra-spec.yaml to draw')
    ap.add_argument('--out', help='the .drawio to write (default: infra-diagram.drawio next to the spec)')
    ap.add_argument('--language', choices=['de', 'en'],
                    help="language of the fixed labels and the decisions panel (default: the spec's context.language, else en); Azure names, types, ranges and roles are never translated")
    args = ap.parse_args()

    if not os.path.isfile(args.path):
        say(f"[skip] {args.path} not found.", 'yellow')
        return 2
    full = os.path.abspath(args.path)
    out = args.out or os.path.join(os.path.dirname(full), 'infra-diagram.drawio')

    # --- Parse -------------------------------------------------------------
    try:
        import yaml
    except ImportError:
        say('[skip] no YAML parser - pip install pyyaml', 'yellow')
        return 2
    try:
        with open(full, encoding='utf-8') as f:
            spec = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        say(f"[fail] YAML does not parse: {e}", 'red')
        return 1

    language = args.language or s((spec.get('context') or {}).get('language')) or 'en'
    if language not in LABELS:
        say(f"[warn] no labels for context.language '{language}' - drawing in English", 'yellow')
        language = 'en'
    T = LABELS[language]

    # --- Read the spec -----------------------------------------------------
    ctx = get_at(spec, ['context']) or {}
    dep = get_at(spec, ['deployment'])
    resources = get_at(spec, ['resources']) or {}

    exposure = s(get_decision(dep, ['network_exposure']))
    net_ownership = s(get_decision(dep, ['network_ownership']))
    obs_ownership = s(get_decision(dep, ['observability_ownership']))
    dns_ownership = s(get_decision(dep, ['private_dns_ownership']))
    is_private = exposure in ('private', 'private_with_exceptions')

    res_keys = sorted(resources.keys())
    has_vnet_res = 'virtual-network' in res_keys
    has_law_res = 'log-analytics-workspace' in res_keys
    draw_vnet = has_vnet_res or net_ownership in ('create', 'reference')
    vnet_existing = (not has_vnet_res) and net_ownership == 'reference'

    compute = [k for k in res_keys if base(k) in COMPUTE_KINDS]
    paas = [k for k in res_keys if base(k) not in COMPUTE_KINDS and base(k) not in MONITOR_KINDS
            and base(k) not in SUPPORT_KINDS and k != 'virtual-network']
    support = [k for k in res_keys if base(k) in SUPPORT_KINDS]
    drawn = compute + paas + support

    def pna(k):
        # The group differs by question set (a workspace keeps it under `access`): networking first,
        # then any other group that carries the decision.
        groups = ['networking'] + [g for g in (resources[k] if isinstance(resources[k], dict) else {}) if g != 'networking']
        for g in groups:
            v = s(get_decision(resources[k], [g, 'public_network_access']))
            if v:
                return v
        return 'disabled' if is_private else 'enabled'

    def pe_subnet_of(k):
        return get_decision(resources[k], ['networking', 'private_endpoint_subnet'])

    # Which resources get a private endpoint: a private posture or an explicit subnet,
    # and not a public-access departure. A Container Apps environment is injected into its
    # subnet (internal), it has no endpoint unless the spec names a subnet for one.
    INJECTED_KINDS = {'container-app', 'container-apps', 'container-apps-environment'}
    with_pe = [k for k in drawn if base(k) not in SUPPORT_KINDS
               and (base(k) not in INJECTED_KINDS or pe_subnet_of(k) is not None)
               and (is_private or pe_subnet_of(k) is not None) and (pna(k) == 'disabled' or pe_subnet_of(k) is not None)]

    # One endpoint per resource, unless it names several subresources (a storage account with
    # blob, queue and table is three).
    n_pe = sum(max(1, len([x for x in as_list(get_decision(resources.get(k), ['networking', 'private_endpoint_subresources'])) if x]))
               for k in with_pe)

    # A private posture with a named departure (a workspace left public) is not "no public access":
    # the subtitle and the footer name the exception instead of claiming everything.
    public_exceptions = [k for k in res_keys if exposure in ('private', 'private_with_exceptions') and base(k) not in SUPPORT_KINDS
                         and k != 'virtual-network' and pna(k) != 'disabled']
    exception_names = ', '.join(dict.fromkeys(TYPE_NAMES.get(base(k), base(k)) for k in public_exceptions))

    pe_subnet_name = subnet_name(get_decision(dep, ['private_endpoint_subnet']), res_keys)
    pe_subnet_prefix = get_decision(dep, ['private_endpoint_subnet_prefix'])
    if not pe_subnet_name:
        # Under network_ownership: create the deployment set holds only the prefix; the
        # generated subnet's name is on the resources that use it.
        for k in with_pe:
            pe_subnet_name = subnet_name(pe_subnet_of(k), res_keys)
            if pe_subnet_name:
                break
    if not pe_subnet_name:
        pe_subnet_name = 'snet-' + T['peSubnet'].lower().replace(' ', '')

    other_subnets = []
    for sn in as_list(get_decision(resources.get('virtual-network'), ['addressing', 'subnets'])):
        if sn is None:
            continue
        if isinstance(sn, dict):
            name = sn.get('name') if sn.get('name') is not None else sn.get('id')
            prefix = sn.get('prefix')
            if prefix is None:
                prefix = sn.get('address_prefix')
            if prefix is None:
                prefix = ', '.join(s(p) for p in as_list(sn.get('address_prefixes')))
        else:
            name, prefix = str(sn), ''
        if name and name != pe_subnet_name:
            other_subnets.append({'name': name, 'prefix': prefix})

    roles = [r for r in as_list(get_decision(spec, ['wiring', 'role_assignments'])) if isinstance(r, dict)]
    zones = [z for z in as_list(get_decision(spec, ['wiring', 'private_dns_zones'])) if z]
    optional = {s(k) for k in as_list(get_decision(spec, ['wiring', 'optional']))}
    purposes = get_decision(spec, ['wiring', 'purposes'])
    purposes = purposes if isinstance(purposes, dict) else {}
    diag_ref = split_ref(get_decision(dep, ['diagnostics_destination']))
    diag_target = diag_ref['name']
    vnet_ref = split_ref(get_decision(dep, ['existing_vnet']))
    draw_law = has_law_res or bool(diag_target)
    has_ai = 'application-insights' in res_keys

    # assumed values anywhere in the spec, by dotted path
    assumed = []

    def find_assumed(node, path):
        if isinstance(node, dict):
            if 'source' in node and s(node['source']) == 'assumed':
                assumed.append(path)
            for k in node:
                find_assumed(node[k], f"{path}.{k}" if path else str(k))

    find_assumed(spec, '')
    open_items = [o for o in as_list(get_at(spec, ['open'])) if o]

    # A resource is flagged when an open or assumed entry points at it or into it.
    def flagged(key):
        prefix = f"resources.{key}"
        if any(a == prefix or a.startswith(prefix + '.') for a in assumed):
            return True
        return any(isinstance(o, dict) and (s(o.get('key')) == prefix or s(o.get('key')).startswith(prefix + '.'))
                   for o in open_items)

    # --- Access: who reaches what ------------------------------------------
    access = []
    seen = set()
    for a in as_list(get_decision(spec, ['wiring', 'access'])):
        if isinstance(a, dict) and a.get('from') and a.get('to'):
            access.append({'from': s(a['from']), 'to': s(a['to']), 'label': s(a.get('label'))})
            seen.add((s(a['from']), s(a['to'])))
    for ra in roles:
        pair = (s(ra.get('from')), s(ra.get('to')))
        if pair not in seen:
            access.append({'from': pair[0], 'to': pair[1], 'label': ''})
            seen.add(pair)
    if exposure == 'public' and not any(a['from'] == 'internet' for a in access):
        for k in (compute or paas):
            access.append({'from': 'internet', 'to': k, 'label': 'HTTPS'})

    # Only these are actors outside the deployment. A name that is neither an actor nor a
    # resource in the spec is a mistake in the spec - drawing it as an actor would put a
    # resource the deployment does not build into the customer's picture.
    def is_actor(name):
        return name in ('internet', 'users') or name.startswith('external:')

    valid = []
    for a in access:
        bad = [n for n in (a['from'], a['to']) if n not in resources and not is_actor(n)]
        if bad:
            say(f"[warn] access {a['from']} -> {a['to']}: '{bad[0]}' is neither a resource in the spec nor internet, users or external:<name> - not drawn", 'yellow')
        else:
            valid.append(a)
    access = valid

    actors = []
    for a in access:
        for name in (a['from'], a['to']):
            if is_actor(name) and name not in actors:
                actors.append(name)

    def actor_base(name):
        return name.split(':', 1)[1] if name.startswith('external:') else name

    def actor_title(name):
        base = actor_base(name)
        if base == 'internet':
            return T['internet']
        if base == 'users':
            return T['users']
        if base in ACTOR_TITLES:
            return ACTOR_TITLES[base]
        return base.replace('-', ' ').title() if base.islower() else base

    # A role assignment is a line on the target's label as well: which role is what a
    # bare arrow cannot say.
    role_lines = {}
    for ra in roles:
        if s(ra.get('to')) in resources:
            role_lines.setdefault(s(ra.get('to')), []).append(f"{s(ra.get('from'))}: {s(ra.get('role'))}")
    # The same on the resource itself: resources.<r>.identity.role_assignments, a list of
    # { principal, role } (per stage or one list). Every principal with its role is a line.
    # ... and identity.data_plane_role_assignments (Cosmos DB's own role model) the same way.
    for rk, rnode in resources.items():
        for group in ('role_assignments', 'data_plane_role_assignments'):
            ras = get_decision(rnode, ['identity', group]) if isinstance(rnode, dict) else None
            for ra in as_list(ras):
                if isinstance(ra, dict) and ra.get('principal') and ra.get('role'):
                    line = f"{s(ra['principal'])}: {s(ra['role'])}"
                    if line not in role_lines.setdefault(rk, []):
                        role_lines[rk].append(line)
    role_principals = {k: {ln.split(':', 1)[0] for ln in v} for k, v in role_lines.items()}

    callers = []
    for a in access:
        if a['from'] in compute and a['to'] in paas and a['from'] not in callers:
            callers.append(a['from'])
    # Side layout: with four or more services the PaaS zone is a column beside the network, as in
    # a hand-drawn architecture - short horizontal lines through a routing channel of their own,
    # one track per caller - and not a block below it that every line has to bend around.
    side = bool(draw_vnet and callers and len(paas) >= 4)
    # PaaS -> PaaS (a search service reading a storage account): a track of its own at the right
    # of the services' column, outside every icon and label. Lines whose runs overlap in height
    # take different lanes; lines that only meet at one icon share a lane.
    pp_lane = {}
    # In the side layout the services stand in two columns with a channel between them: four
    # services are two rows, not a column four slots tall beside a network of one (the single
    # column left everything under the network empty). The PaaS -> PaaS lines run in that
    # channel - out of the side of the source that faces it, down or up, in at the facing side of
    # the target - and never across the neighbour in the row. Lines whose rows overlap or touch
    # take different lanes.
    pp_edges = [a for a in access if a['from'] in paas and a['to'] in paas and a['from'] != a['to']]
    # Three columns from seven services on, as long as no PaaS -> PaaS line needs the channel
    # between the first two: eight services in two columns are four rows beside a network of one.
    PAAS_COLS = 3 if len(paas) >= 7 and not pp_edges else 2
    if side:
        pp_iv = []   # per lane: occupied (top, bottom) row intervals
        row_of = lambda k: paas.index(k) // PAAS_COLS
        for a in sorted(pp_edges, key=lambda a: abs(row_of(a['from']) - row_of(a['to']))):
            lo, hi = sorted((row_of(a['from']), row_of(a['to'])))
            for ln, iv in enumerate(pp_iv):
                if all(hi < l or lo > h for l, h in iv):
                    iv.append((lo, hi))
                    break
            else:
                ln = len(pp_iv)
                pp_iv.append([(lo, hi)])
            pp_lane[(a['from'], a['to'])] = ln
    # the channel: a gap that keeps the two columns' labels apart, plus one track per lane
    pp_chan = 24 + (TRK * (max(pp_lane.values()) + 1) if pp_lane else 0)
    callers_of = {}
    callers_listed_in_roles = set()   # callers whose role is already on the label
    for a in access:
        if a['from'] in compute and a['to'] in paas:
            who = TYPE_NAMES.get(base(a['from']), base(a['from'])) + (f" &#183; {a['from'].partition('__')[2]}" if '__' in a['from'] else '')
            callers_of.setdefault(a['to'], []).append(who + (f" ({a['label']})" if a.get('label') else ''))
            if a['from'] in role_principals.get(a['to'], ()):
                callers_listed_in_roles.add((a['to'], who))

    def display_name(p):
        """A principal as the picture names it: the kind's title and the instance, not the spec key
        (`user-assigned-identity__web` -> `Managed Identity · web`), which wrapped at every hyphen."""
        if p in resources or base(p) in TYPE_NAMES:
            return TYPE_NAMES.get(base(p), base(p)) + (f" · {p.partition('__')[2]}" if '__' in p else '')
        return p

    def resource_label(k):
        kind_title = TYPE_NAMES.get(base(k), base(k).replace('-', ' ').title())
        sub = s(purposes.get(k)) or (k.partition('__')[2] or k)
        note = ' · '.join(n for n in (T['noSet'] if not has_question_set(base(k)) else '', T['optional'] if k in optional else '') if n)
        label = format_label(kind_title, sub, note)
        if k in public_exceptions:
            label += f"<br><font style='font-size:10px' color='{PUBLIC_COLOR}'>&#9888; {esc(T['publicMark'])}</font>"
        for line in role_lines.get(k, []):
            principal, _, role = line.partition(': ')
            label += f"<br><font style='font-size:10px' color='#5C2D91'>&#8592; {esc(display_name(principal))}: {esc(role)}</font>"
        rest = [c for c in callers_of.get(k, []) if (k, c.split(' (')[0]) not in callers_listed_in_roles]
        if side and rest:
            label += f"<br><font style='font-size:10px' color='#5C2D91'>&#8592; {', '.join(rest)}</font>"
        return label

    labels = {k: resource_label(k) for k in drawn + (['application-insights'] if has_ai else [])}
    pitch = {k: pitch_of(labels[k]) for k in drawn}

    # --- Geometry, phase A: sizes ------------------------------------------
    def compute_subnet(k):
        n = subnet_name(get_decision(resources[k], ['networking', 'integration_subnet'])
                        or get_decision(resources[k], ['environment', 'infrastructure_subnet']), res_keys)
        if n:
            return n
        for sn in other_subnets:
            if 'integration' in sn['name'] or 'app' in sn['name']:
                return sn['name']
        return other_subnets[0]['name'] if other_subnets else T['computeSubnet']

    groups = {}
    for k in compute:
        groups.setdefault(compute_subnet(k), []).append(k)
    meta = {sn['name']: sn for sn in other_subnets}
    strips = [sn for sn in other_subnets if sn['name'] not in groups]

    def rows_of(keys, cols):
        return [keys[i:i + cols] for i in range(0, len(keys), cols)]

    def rows_height(keys, cols, gutter=0):
        rows = rows_of(keys, cols)
        return sum(max(pitch[k] for k in r) for r in rows) + gutter * max(len(rows) - 1, 0)

    cols_c = min(max([len(v) for v in groups.values()] or [1]), 4)
    # Up to five services in one row; more wrap into two, the second row shifted by half a slot, so
    # that the line to a second-row icon comes down in the gap between two first-row icons and not
    # through one. A narrower row means a narrower network and less empty space in it.
    n_inter = sum(1 for a in access if a['from'] in compute and a['to'] in compute)
    if side:
        # Hub layout, after the hand-drawn ones: compute subnets | collector tracks | the endpoint
        # column | one trunk | the services. Callers run into the endpoints, one line each; from
        # there one line leaves for each service. Who calls what is text at the service.
        cols_p = PAAS_COLS
        stagger = 0
        cw = max(cols_c * SLOT_W + 2 * PAD, 2 * SLOT_W + 2 * PAD)        # compute subnet width
        coll_w = 34 + TRK * (len(callers) + n_inter)
        pe_w = SLOT_W
        w_main = PAD + cw + coll_w + pe_w + PAD
        chan_w = 80
        paas_w = cols_p * SLOT_W + (cols_p - 1) * pp_chan + 2 * PAD
    else:
        cols_p = len(paas) if len(paas) <= 5 else math.ceil(len(paas) / 2)
        cols_p = min(max(cols_p, 1), 8)
        stagger = SLOT_W // 2 if len(paas) > cols_p else 0
        w_main = max(cols_c * SLOT_W + 4 * PAD, cols_p * SLOT_W + stagger + 2 * PAD, min(len(support), cols_p) * SLOT_W + 2 * PAD, 2 * SLOT_W + 4 * PAD)
        chan_w = paas_w = 0
    block_w = w_main + (chan_w + paas_w if side else 0)   # what the zones below the network span

    # What the spec says each subnet is delegated to wins; the kind's usual delegation is the
    # fallback for a spec that does not say.
    spec_deleg = {s(d.get('subnet')): s(d.get('service'))
                  for d in as_list(get_decision(resources.get('virtual-network'), ['subnet_policy', 'subnet_delegations']))
                  if isinstance(d, dict)}

    def delegation(keys, name=''):
        if name in spec_deleg:
            return f"{T['delegated']} {spec_deleg[name]}"
        for k in keys:
            if base(k) in DELEGATIONS:
                return f"{T['delegated']} {DELEGATIONS[base(k)]}"
        return ''

    group_boxes = []   # (name, keys, header_h, h)
    for name, keys in groups.items():
        hh = 28 + (14 if delegation(keys, name) else 0)
        group_boxes.append((name, keys, hh, hh + rows_height(keys, cols_c) + 6))

    show_pe = draw_vnet and bool(with_pe)
    pe_box_h = ZHEAD + SLOT_H + 10
    vn_h = 0
    if draw_vnet:
        vn_h = HEAD
        for _, _, _, h in group_boxes:
            vn_h += h + PAD
        if show_pe and not side:
            vn_h += pe_box_h + PAD
        vn_h += len(strips) * (44 + 10)
        vn_h += PAD - (10 if strips else 0)
    elif compute:
        vn_h = ZHEAD + rows_height(compute, cols_c) + PAD
    PAAS_TOP, PAAS_TITLE = 14, 26
    paas_h = (PAAS_TOP + rows_height(paas, cols_p) + PAAS_TITLE) if paas else 0
    GUT = 16   # side layout: the gap between two rows of services; a line to a second-column service runs in it
    if side:
        PAAS_HEAD = 44   # the title, then the first row's gutter
        paas_h = PAAS_HEAD + rows_height(paas, cols_p, GUT) + PAD
    # One bus lane per compute resource that calls PaaS, between the network and the PaaS zone.
    gap = 30 + 10 * len(callers)

    # The lower zones - identities and security groups, monitoring, name resolution - sit under
    # the network and the services, never in a column of their own at the right: a picture that
    # has to fit a page is built downwards. Created zones go inside the group, referenced
    # (existing) ones below it.
    cols_s = min(max(len(support), 1), max((w_main - 2 * PAD) // SLOT_W, 1))
    support_h = (ZHEAD + rows_height(support, cols_s) + PAD) if support else 0
    law_existing = (not has_law_res) and obs_ownership != 'create'
    dns_existing = dns_ownership != 'deployment'
    lower, outside = [], []   # dicts: id, w, h (dx, dy once placed)
    if support:
        lower.append({'id': 'support', 'w': cols_s * SLOT_W + 2 * PAD, 'h': support_h})
    ai_h = max(SLOT_H, pitch_of(labels['application-insights'])) if has_ai else 0   # roles make its label taller
    if draw_law or has_ai:
        z = {'id': 'monitoring', 'w': ZONE_W, 'h': ZHEAD + (SLOT_H if draw_law else 0) + ai_h + 40 + PAD}
        (outside if law_existing else lower).append(z)
    if zones or dns_existing and dns_ownership:
        z = {'id': 'dnszones', 'w': ZONE_W, 'h': ZHEAD + SLOT_H + PAD}
        (outside if dns_existing else lower).append(z)

    def flow(items, width):
        """Packs the zones left to right in rows of `width`; sets dx, dy; returns the height."""
        x = y = row_h = 0
        for it in items:
            if x and x + it['w'] > width:
                x, y, row_h = 0, y + row_h + PAD, 0
            it['dx'], it['dy'] = x, y
            x += it['w'] + PAD
            row_h = max(row_h, it['h'])
        return (y + row_h) if items else 0

    if side:
        # Under the network or under the services: whichever split keeps the group shortest.
        # The support zone stays under the network, where the identities belong.
        fixed = [z for z in lower if z['id'] == 'support']
        movable = [z for z in lower if z['id'] != 'support']
        best = None
        for mask in range(2 ** len(movable)):
            left = fixed + [z for i, z in enumerate(movable) if not mask >> i & 1]
            right = [z for i, z in enumerate(movable) if mask >> i & 1]
            lh = vn_h + ((PAD + flow(left, w_main)) if left else 0)
            rh = paas_h + ((PAD + flow(right, paas_w)) if right else 0)
            if best is None or max(lh, rh) < best[0]:
                best = (max(lh, rh), left, right)
        main_h, lower_left, lower_right = best
        flow(lower_left, w_main)
        flow(lower_right, paas_w)
    else:
        lower_left, lower_right = lower, []
        main_h = vn_h + (gap if (vn_h and paas_h) else 0) + paas_h + ((PAD + flow(lower_left, w_main)) if lower_left else 0)
    # A telemetry line to the monitoring zone needs a corridor right of the network; in the side
    # layout the channel to the services is one, otherwise the group is widened by a strip.
    n_mon = any(a['from'] in compute and base(a['to']) in MONITOR_KINDS for a in access)

    # --- Geometry, phase B: positions --------------------------------------
    ext_w = ZONE_W if actors else 0
    # No subscription frame: it changes per environment and only adds a layer.
    # Each line between an actor and a compute resource runs on a track of its own in the gap.
    n_ae = sum(1 for a in access if (is_actor(a['from']) and a['to'] in compute) or (is_actor(a['to']) and a['from'] in compute))
    ACT_STEP = 36
    ext_gap = 40 + ACT_STEP * max(n_ae - 1, 0)
    rg_x, rg_y = 20 + (ext_w + ext_gap if actors else 0), TOP
    sub_x, sub_y = rg_x, rg_y
    main_x, main_y = rg_x + PAD, rg_y + HEAD + 10
    rg_w = main_x + block_w + PAD + (24 if n_mon and not side else 0) - rg_x
    content_h = max(main_h, 140)
    rg_h = HEAD + 10 + content_h + PAD + (24 if is_private else 0)
    sub_w, sub_h = rg_w, rg_h   # the extent the legend and the panel line up with

    # --- Cells -------------------------------------------------------------
    containers, icons = [], []

    def add_container(c):
        containers.append(c)
        return c

    def add_icon(cid, parent, slot_x, slot_y, kind, label, is_flagged=False, existing=False, slot_h=SLOT_H, warn=True):
        img = ICONS.get(kind)
        if img:
            style = icon_style(img, is_flagged, existing)
            x, y, w, h = slot_x + (SLOT_W - ICON) / 2, slot_y + 8, ICON, ICON
        else:
            if warn:
                say(f"[warn] no icon for '{kind}' - drawn as a box", 'yellow')
            style = 'rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#605E5C;'
            if existing:
                style += 'opacity=60;'
            if is_flagged:
                style += 'fontColor=#D13438;'
            x, y, w, h = slot_x + 20, slot_y + 8, SLOT_W - 40, ICON
            # The box holds the title; the rest of the label sits below it like an icon's,
            # since a 48px box cannot hold four lines.
            title, _, rest = label.partition('<br>')
            label = title
            if rest:
                icons.append({'id': f"{cid}-icon", 'parent': parent, 'x': x, 'y': y + h + 2, 'w': w, 'h': 16 * label_lines(rest) + 4,
                              'style': 'text;html=1;align=center;verticalAlign=top;whiteSpace=wrap;', 'value': rest})
        icons.append({'id': cid, 'parent': parent, 'x': x, 'y': y, 'w': w, 'h': h, 'style': style, 'value': label,
                      'slot': {'x': slot_x, 'y': slot_y, 'w': SLOT_W, 'h': slot_h}, 'labelBelow': bool(img)})

    def place_grid(keys, parent, gx, gy, cols, stagger=0, col_gap=0, gutter=0):
        y = gy
        for r, row in enumerate(rows_of(keys, cols)):
            rh = max(pitch[k] for k in row)
            for c, k in enumerate(row):
                add_icon(f"res-{k}", parent, gx + c * (SLOT_W + col_gap) + (stagger if r % 2 else 0), y, base(k), labels[k], flagged(k), k in optional, slot_h=rh)
            y += rh + gutter

    def add_text(cid, parent, x, y, w, h, value, style):
        icons.append({'id': cid, 'parent': parent, 'x': x, 'y': y, 'w': w, 'h': h, 'style': style, 'value': value})

    # Title and subtitle
    workload = s(get_value(ctx.get('workload'))) or s(get_at(spec, ['spec', 'id']))
    sub_line = {'private': T['subPrivate'], 'private_with_exceptions': T['subExc'], 'public': T['subPublic']}.get(exposure, '')
    if exposure in ('private', 'private_with_exceptions') and public_exceptions:
        sub_line = T['subPrivateExc'].replace('{names}', exception_names)
    if sub_line and s(get_decision(dep, ['local_auth'])) == 'disabled':
        sub_line += T['keyless']
    add_text('title', '1', 20, 12, 900, 30, f"<b>{esc(workload)} &#8212; {T['arch']}</b>",
             'text;html=1;align=left;verticalAlign=middle;fontSize=20;')
    if sub_line:
        add_text('subtitle', '1', 20, 46, 1300, 22, esc(sub_line), 'text;html=1;align=left;verticalAlign=middle;fontSize=12;fontColor=#605E5C;')

    # External zone with its actors
    actor_ids = {}
    if actors:
        ext_h = ZHEAD + len(actors) * 110 + PAD
        add_container({'id': 'z-ext', 'parent': '1', 'x': 20, 'y': main_y, 'w': ext_w, 'h': ext_h, 'style': ZONES['external'], 'value': esc(T['ext'])})
        for i, name in enumerate(actors):
            cid = f"act-{re.sub('[^a-z0-9]+', '-', name.lower())}"
            actor_ids[name] = cid
            slot_x, slot_y = 20 + (ext_w - SLOT_W) / 2, main_y + ZHEAD + i * 110
            if actor_base(name) == 'internet':
                icons.append({'id': cid, 'parent': 'z-ext', 'x': slot_x + (SLOT_W - 64) / 2, 'y': slot_y + 8, 'w': 64, 'h': 44,
                              'style': 'ellipse;shape=cloud;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#605E5C;verticalLabelPosition=bottom;verticalAlign=top;labelBackgroundColor=none;',
                              'value': f"<b>{esc(actor_title(name))}</b>",
                              'slot': {'x': slot_x, 'y': slot_y, 'w': SLOT_W, 'h': 110}, 'labelBelow': True})
            else:
                add_icon(cid, 'z-ext', slot_x, slot_y, actor_base(name), f"<b>{esc(actor_title(name))}</b>", False, False, slot_h=110, warn=False)

    # Resource group
    loc = s(get_value(ctx.get('location')))
    env_ = ' · '.join(s(e) for e in as_list(get_value(ctx.get('environments'))) if s(e)) or s(get_value(ctx.get('environment')))
    rg_name = get_value(ctx.get('resource_group_name'))
    rg_label = format_label(s(rg_name if rg_name is not None else T['rg']), ' · '.join(p for p in (loc, env_) if p != ''), '')
    add_container({'id': 'rg', 'parent': '1', 'x': rg_x, 'y': rg_y, 'w': rg_w, 'h': rg_h, 'style': CONTAINER_STYLE, 'value': rg_label})
    icons.append({'id': 'rg-icon', 'parent': 'rg', 'x': rg_x + 6, 'y': rg_y + 6, 'w': 24, 'h': 24,
                  'style': f"image;aspect=fixed;html=1;image={ICONS['resource-group']};", 'value': ''})
    if is_private:
        footer = T['noPublicExc'].replace('{names}', exception_names) if public_exceptions else T['noPublic']
        add_text('rg-private', 'rg', rg_x + PAD, rg_y + rg_h - 26, rg_w - 2 * PAD, 20, f"&#128274; {esc(footer)}",
                 'text;html=1;align=left;verticalAlign=middle;fontColor=#107C10;fontStyle=2;')

    # Network zone: subnets with their compute, then the bundled endpoints
    vn_sub = ''
    paas_y = main_y if side else main_y + vn_h + (gap if (vn_h and paas_h) else 0)
    paas_x = main_x + w_main + chan_w if side else main_x
    bus_base = main_y + vn_h + 14
    # An open entry on the network - the address space, a subnet prefix, the subnet plan - colours
    # the network and its subnets red like a resource with an open entry; before, only resource
    # icons were flagged and the network read as decided.
    net_open = flagged('virtual-network') or any(
        isinstance(o, dict) and s(o.get('key')).startswith(('deployment.address_space', 'deployment.private_endpoint_subnet', 'deployment.subnet'))
        for o in open_items)
    redn = (lambda h: f"<font color='#D13438'>{h}</font>") if net_open else (lambda h: h)
    if draw_vnet:
        vn_name = vnet_ref['name'] if (vnet_existing and vnet_ref['name']) else 'Virtual Network'
        addr = get_decision(dep, ['address_space'])
        if addr is None:
            addr = get_decision(resources.get('virtual-network'), ['addressing', 'address_space'])
        vn_sub = s(addr)
        vn_note = T['existing'] if vnet_existing else ''
        style = CONTAINER_STYLE + (EXISTING_STYLE if vnet_existing else '')
        add_container({'id': 'vnet', 'parent': 'rg', 'x': main_x, 'y': main_y, 'w': w_main, 'h': vn_h, 'style': style, 'value': redn(format_label(vn_name, vn_sub, vn_note))})
        icons.append({'id': 'vnet-icon', 'parent': 'vnet', 'x': main_x + 6, 'y': main_y + 6, 'w': 24, 'h': 24,
                      'style': f"image;aspect=fixed;html=1;image={ICONS['virtual-network']};", 'value': ''})
        sn_x, sn_w, cursor = main_x + PAD, w_main - 2 * PAD, main_y + HEAD
        sn_style = SUBNET_STYLE + (EXISTING_STYLE if vnet_existing else '')
        for gi, (name, keys, hh, h) in enumerate(group_boxes):
            prefix = s(meta.get(name, {}).get('prefix'))
            note = delegation(keys, name)
            lbl = f"<b>{esc(name)}</b>" + (f"  <font style='font-size:10px'>{esc(prefix)}</font>" if prefix else '')
            if note:
                lbl += f"<br><font style='font-size:10px'><i>{esc(note)}</i></font>"
            add_container({'id': f"snet-c{gi}", 'parent': 'vnet', 'x': sn_x, 'y': cursor, 'w': cw if side else sn_w, 'h': h, 'style': sn_style, 'value': redn(lbl)})
            place_grid(keys, f"snet-c{gi}", sn_x + PAD, cursor + hh, cols_c)
            cursor += h + PAD
        if show_pe and side:
            # the endpoint column, as tall as the compute subnets beside it; the bundle in its middle
            col_h = cursor - PAD - (main_y + HEAD)
            pe_x = sn_x + cw + coll_w
            pe_label = f"<b>{esc(pe_subnet_name)}</b>" + (f"  <font style='font-size:10px'>{esc(pe_subnet_prefix)}</font>" if pe_subnet_prefix else '')
            add_container({'id': 'snet-pe', 'parent': 'vnet', 'x': pe_x, 'y': main_y + HEAD, 'w': pe_w, 'h': col_h, 'style': sn_style, 'value': redn(pe_label)})
            kinds = list(dict.fromkeys(TYPE_NAMES.get(base(k), base(k)) for k in with_pe))
            names = ', '.join(kinds[:2]) + (f" +{len(kinds) - 2}" if len(kinds) > 2 else '')
            add_icon('pe-bundle', 'snet-pe', pe_x, main_y + HEAD + (col_h - SLOT_H) / 2, 'private-endpoint',
                     format_label(T['peBundle'], f"{n_pe}× {names}", ''), slot_h=SLOT_H)
        elif show_pe:
            pe_label = f"<b>{esc(pe_subnet_name)}</b>" + (f"  <font style='font-size:10px'>{esc(pe_subnet_prefix)}</font>" if pe_subnet_prefix else '')
            add_container({'id': 'snet-pe', 'parent': 'vnet', 'x': sn_x, 'y': cursor, 'w': sn_w, 'h': pe_box_h, 'style': sn_style, 'value': redn(pe_label)})
            kinds = list(dict.fromkeys(TYPE_NAMES.get(base(k), base(k)) for k in with_pe))
            names = ', '.join(kinds[:2]) + (f" +{len(kinds) - 2}" if len(kinds) > 2 else '')
            add_icon('pe-bundle', 'snet-pe', sn_x + PAD, cursor + ZHEAD, 'private-endpoint',
                     format_label(T['peBundle'], f"{n_pe}× {names}", ''), slot_h=SLOT_H)
            cursor += pe_box_h + PAD
        for j, sn in enumerate(strips):
            lbl = f"<b>{esc(sn['name'])}</b>" + (f"  <font style='font-size:10px'>{esc(sn['prefix'])}</font>" if sn['prefix'] else '')
            add_container({'id': f"snet-{j}", 'parent': 'vnet', 'x': sn_x, 'y': cursor, 'w': sn_w, 'h': 44, 'style': sn_style, 'value': redn(lbl)})
            cursor += 44 + 10
    elif compute:
        add_container({'id': 'z-compute', 'parent': 'rg', 'x': main_x, 'y': main_y, 'w': w_main, 'h': vn_h, 'style': ZONES['compute'], 'value': esc(T['compute'])})
        place_grid(compute, 'z-compute', main_x + PAD, main_y + ZHEAD, cols_c)

    # PaaS zone
    if paas:
        all_private = all(pna(k) == 'disabled' for k in paas)
        title = f"{T['paas']} &#8212; {esc(T['paasPrivate'])}" if all_private else T['paas']
        if side:
            # the lines come in from the left here, so the title can stay at the top
            add_container({'id': 'z-paas', 'parent': 'rg', 'x': paas_x, 'y': paas_y, 'w': paas_w, 'h': paas_h, 'style': ZONES['paas'], 'value': title})
            place_grid(paas, 'z-paas', paas_x + PAD, paas_y + PAAS_HEAD, cols_p, col_gap=pp_chan, gutter=GUT)
        else:
            add_container({'id': 'z-paas', 'parent': 'rg', 'x': main_x, 'y': paas_y, 'w': w_main, 'h': paas_h, 'style': ZONES['paas_in'], 'value': title})
            place_grid(paas, 'z-paas', main_x + PAD, paas_y + PAAS_TOP, cols_p, stagger)
    def draw_zone(z, zx, zy, parent):
        zid = z['id']
        if zid == 'support':
            add_container({'id': 'z-support', 'parent': parent, 'x': zx, 'y': zy, 'w': z['w'], 'h': z['h'], 'style': ZONES['paas'], 'value': esc(T['support'])})
            place_grid(support, 'z-support', zx + PAD, zy + ZHEAD, cols_s)
            return
        is_mon = zid == 'monitoring'
        existing = law_existing if is_mon else dns_existing
        add_container({'id': f"z-{zid}", 'parent': parent, 'x': zx, 'y': zy, 'w': ZONE_W, 'h': z['h'],
                       'style': (ZONES['monitoring'] if is_mon else ZONES['platform']) + (EXISTING_STYLE if existing else ''),
                       'value': esc(T['monitoring'] if is_mon else T['nameRes'])})
        sx, sy = zx + (ZONE_W - SLOT_W) / 2, zy + ZHEAD
        if is_mon:
            if draw_law:
                law_name = s(purposes.get('log-analytics-workspace')) or (s(diag_target) if diag_target else 'log-analytics-workspace')
                law_label = format_label('Log Analytics', law_name, T['existing'] if existing else '')
                if 'log-analytics-workspace' in public_exceptions:
                    law_label += f"<br><font style='font-size:10px' color='{PUBLIC_COLOR}'>&#9888; {esc(T['publicMark'])}</font>"
                add_icon('law', f"z-{zid}", sx, sy, 'log-analytics-workspace', law_label,
                         flagged('log-analytics-workspace'), existing)
                sy += SLOT_H
            if has_ai:
                add_icon('res-application-insights', f"z-{zid}", sx, sy, 'application-insights',
                         labels['application-insights'], flagged('application-insights'), slot_h=ai_h)
                sy += ai_h
            add_text('diag-note', f"z-{zid}", zx + 12, sy + 4, ZONE_W - 24, 32, f"<i>{esc(T['diagNote'])}</i>",
                     'text;html=1;align=center;verticalAlign=middle;whiteSpace=wrap;fontSize=10;fontColor=#605E5C;')
        else:
            add_icon('dns', f"z-{zid}", sx, sy, 'private-dns-zone',
                     format_label('Private DNS Zones', f"{len(zones)}× privatelink.*" if zones else 'privatelink.*', T['existing'] if existing else ''),
                     False, existing)

    # The lower zones: under the network (and, in the side layout, under the services); the
    # referenced ones in a row below the group, the legend under those.
    left_y0 = (main_y + vn_h + PAD) if side else paas_y + (paas_h + PAD if paas else (PAD if vn_h else 0))
    columns = [(lower_left, main_x, left_y0, 'rg')]
    if side:
        columns.append((lower_right, paas_x, main_y + paas_h + PAD, 'rg'))
    out_y = rg_y + rg_h + 30
    out_h = flow(outside, rg_w)
    columns.append((outside, rg_x, out_y, '1'))
    legend_y = out_y + (out_h + 30 if outside else 0)
    for items, x0, y0, parent in columns:
        for z in items:
            draw_zone(z, x0 + z['dx'], y0 + z['dy'], parent)

    # --- Edges: access -----------------------------------------------------
    by_id = {c['id']: c for c in containers + icons}
    edges = []
    caller_i = {k: i for i, k in enumerate(callers)}

    def node_id(name):
        return f"res-{name}" if name in resources else actor_ids.get(name)

    def is_outside(name):
        return is_actor(name) and (name == 'internet' or name.startswith('external:'))

    def is_public_edge(a):
        # Either end outside the deployment, or a target whose public access is not disabled.
        if is_outside(a['from']) or is_outside(a['to']):
            return True
        return a['to'] in drawn and pna(a['to']) != 'disabled'

    # Routing. A caller leaves its icon to the right and drops on a track of its own in the free
    # space at the right of the subnets - never through another icon - to its lane below the
    # network, where it fans out to its targets.
    #   - Tracks are assigned right to left from the top caller down: a lower caller's horizontal
    #     run then ends before the track of an upper one, so tracks never cross a run.
    #   - Lanes are assigned by number of targets, fewest on top: a drop crosses the lanes below
    #     its own, so the callers with the shortest drops sit lowest.
    node_of = {k: node_id(k) for k in callers}
    by_top = sorted(callers, key=lambda k: by_id[node_of[k]]['y'] if node_of[k] in by_id else 0)
    track_rank = {k: i for i, k in enumerate(by_top)}
    tgt_count = {k: sum(1 for a in access if a['from'] == k and a['to'] in paas) for k in callers}
    lane_rank = {k: i for i, k in enumerate(sorted(callers, key=lambda k: (tgt_count[k], track_rank[k])))}
    dense = len(callers) >= 3
    caller_color = {k: CALLER_COLORS[i % len(CALLER_COLORS)] for i, k in enumerate(by_top)}
    vn_cell = by_id.get('vnet') or by_id.get('z-compute')
    gut0 = (vn_cell['x'] + vn_cell['w'] - 2 * PAD) if vn_cell else sub_x
    inter = {}   # compute -> compute: tracks left of the callers' own
    actor_edges = [a for a in access if (is_actor(a['from']) and a['to'] in compute) or (is_actor(a['to']) and a['from'] in compute)]
    actor_edges = [a for a in actor_edges if node_id(a['from']) in by_id and node_id(a['to']) in by_id]
    ay = lambda a: by_id[node_id(a['from'] if is_actor(a['from']) else a['to'])]['y']
    actor_edges.sort(key=lambda a: (ay(a), a['from'], a['to']))
    gx_of = {(a['from'], a['to']): 20 + ext_w + 14 + ACT_STEP * (len(actor_edges) - 1 - i) for i, a in enumerate(actor_edges)}
    at_comp = {}
    for a in actor_edges:
        at_comp.setdefault(a['to'] if is_actor(a['from']) else a['from'], []).append(a)
    # A compute that is the target of a compute -> compute line takes that line high on its right
    # side and sends its own lines to the endpoints from lower down, so an arrowhead never lands
    # where another line leaves.
    IN_FR, OUT_FR = 0.25, 0.75
    inter_tgt = {a['to'] for a in access if a['from'] in compute and a['to'] in compute}
    PP_FR = (0.7, 0.3, 0.5)   # anchor heights for lines sharing one side of an icon
    pp_side = {}               # (resource, side) -> the PaaS -> PaaS lines already anchored there
    pp_touched = {a['from'] for a in pp_edges} | {a['to'] for a in pp_edges}
    gap_edges = 0  # actors <-> compute: tracks in the gap between the external zone and the group,
                   # so a vertical run never lies on the resource group's border
    for n, a in enumerate(access):
        src, dst = node_id(a['from']), node_id(a['to'])
        if src not in by_id or dst not in by_id:
            say(f"[warn] access {a['from']} -> {a['to']}: endpoint not drawn", 'yellow')
            continue
        if side and a['from'] in caller_i and a['to'] in paas:
            continue   # drawn as caller -> endpoints -> service, below
        public = is_public_edge(a)
        color = PUBLIC_COLOR if public else (caller_color.get(a['from'], PRIVATE_COLOR) if dense else PRIVATE_COLOR)
        style = EDGE_BASE + f"strokeColor={color};fontColor={color};fontSize=10;labelBackgroundColor=#FFFFFF;"
        sc, dc = by_id[src], by_id[dst]
        edge_label = a['label'] or (T['telemetry'] if a['from'] in compute and base(a['to']) in MONITOR_KINDS else '')
        edge = {'id': f"e-{n}", 'source': src, 'target': dst, 'value': edge_label}
        if a['from'] in caller_i and a['to'] in paas:
            tx = gut0 - 16 * track_rank[a['from']]
            bus_y = bus_base + 10 * lane_rank[a['from']]
            tcx = dc['x'] + dc['w'] / 2
            if a['from'] in at_comp:
                # actor lines end at the icon's left at mid height; the trunk leaving at the same
                # height read as one line through the icon, so it leaves over the top
                top = sc['slot']['y'] + 2
                edge['style'] = style + 'exitX=0.5;exitY=0;entryX=0.5;entryY=0;'
                edge['points'] = [{'x': sc['x'] + sc['w'] / 2, 'y': top}, {'x': tx, 'y': top}, {'x': tx, 'y': bus_y}, {'x': tcx, 'y': bus_y}]
            else:
                edge['style'] = style + 'exitX=1;exitY=0.5;entryX=0.5;entryY=0;'
                edge['points'] = [{'x': tx, 'y': sc['y'] + sc['h'] / 2}, {'x': tx, 'y': bus_y}, {'x': tcx, 'y': bus_y}]
            if edge_label:
                # beside the line's own drop into its target, not on the shared run
                path = [(sc['x'] + sc['w'], sc['y'] + sc['h'] / 2)] + [(p['x'], p['y']) for p in edge['points']] + [(tcx, dc['y'])]
                seg = [abs(x2 - x1) + abs(y2 - y1) for (x1, y1), (x2, y2) in zip(path, path[1:])]
                if sum(seg):
                    edge['lx'] = round(2 * ((sum(seg[:-1]) + 0.5 * seg[-1]) / sum(seg)) - 1, 3)
                    edge['off'] = (8 + 3 * plain_len(edge_label), 0)
        elif a['from'] in compute and a['to'] in compute:
            k = inter.setdefault(a['from'] + '>' + a['to'], len(inter))
            if side and 'snet-pe' in by_id:
                tx = by_id['snet-pe']['x'] - coll_w + 14 + TRK * (len(callers) + k)
            else:
                tx = gut0 - 16 * (len(callers) + 1 + k)
            edge['style'] = style + f"exitX=1;exitY=0.5;entryX=1;entryY={IN_FR};"
            edge['points'] = [{'x': tx, 'y': sc['y'] + sc['h'] / 2}, {'x': tx, 'y': dc['y'] + dc['h'] * IN_FR}]
        elif a['from'] in compute and base(a['to']) in MONITOR_KINDS:
            # To the monitoring zone, which sits below the network or the services: down a
            # corridor right of the network, along the gutter above the zone's row, down beside
            # the zone, in at the icon's left - never across another zone or a service line.
            zone = by_id.get('z-monitoring')
            style = EDGE_BASE + f"strokeColor={PUBLIC_COLOR if public else PRIVATE_COLOR};fontColor={PUBLIC_COLOR if public else PRIVATE_COLOR};fontSize=10;labelBackgroundColor=#FFFFFF;"
            gx = (zone['x'] - 8) if zone else dc['x'] - 22
            gutter_y = (zone['y'] - PAD / 2) if zone else dc['y'] - 20
            mid = dc['y'] + dc['h'] / 2
            if side:
                # Leaves the icon low on its right side on a track of its own (the endpoint line
                # leaves at mid height), drops to the strip under the endpoint subnet and runs out
                # below it into the channel, so it never lies on a line to the endpoints.
                tx = vn_cell['x'] + vn_cell['w'] + 54
                ex_y = sc['y'] + sc['h'] * 0.9
                sub = by_id.get(sc['parent'])
                xa = (sub['x'] + sub['w'] + 12) if sub else sc['x'] + sc['w'] + 40
                pe_sn = by_id.get('snet-pe')
                yg = (pe_sn['y'] + pe_sn['h'] + 16) if pe_sn else ex_y + 40
                edge['style'] = style + 'exitX=1;exitY=0.9;entryX=0;entryY=0.5;'
                pts = [{'x': xa, 'y': ex_y}, {'x': xa, 'y': yg}, {'x': tx, 'y': yg}, {'x': tx, 'y': gutter_y}, {'x': gx, 'y': gutter_y}, {'x': gx, 'y': mid}]
            else:
                tx = (vn_cell['x'] + vn_cell['w'] + 20) if vn_cell else sc['x'] + sc['w'] + 40
                ex_y = sc['y'] + sc['h'] / 2
                edge['style'] = style + 'exitX=1;exitY=0.5;entryX=0;entryY=0.5;'
                pts = [{'x': tx, 'y': ex_y}, {'x': tx, 'y': gutter_y}, {'x': gx, 'y': gutter_y}, {'x': gx, 'y': mid}]
            edge['points'] = pts
            # label on the first run, near the icon
            path = [(sc['x'] + sc['w'], ex_y)] + [(p['x'], p['y']) for p in pts] + [(dc['x'], mid)]
            seg = [abs(x2 - x1) + abs(y2 - y1) for (x1, y1), (x2, y2) in zip(path, path[1:])]
            if sum(seg):
                edge['lx'] = round(2 * ((seg[0] + 0.5 * seg[1]) / sum(seg)) - 1, 3)
        elif side and a['from'] in paas and a['to'] in paas:
            # Through the channel between the two columns: out of the side of the source that faces
            # it, along a lane of its own, in at the facing side of the target. The label sits on
            # the vertical run, in the channel.
            sc_col, dc_col = paas.index(a['from']) % cols_p, paas.index(a['to']) % cols_p
            lx_track = paas_x + PAD + SLOT_W + 12 + TRK * pp_lane.get((a['from'], a['to']), 0)
            # Two lines on one side of an icon take different heights (0.7, then 0.3); the trunk
            # into a first-column service enters at 0.3 when such a line leaves it at 0.7, so two
            # lines never meet at one height and read as one line through the icon.
            fr_s = PP_FR[pp_side.setdefault((a['from'], 'R' if sc_col == 0 else 'L'), []).__len__() % len(PP_FR)]
            pp_side[(a['from'], 'R' if sc_col == 0 else 'L')].append(a)
            fr_d = PP_FR[pp_side.setdefault((a['to'], 'R' if dc_col == 0 else 'L'), []).__len__() % len(PP_FR)]
            pp_side[(a['to'], 'R' if dc_col == 0 else 'L')].append(a)
            sy_, dy_ = sc['y'] + sc['h'] * fr_s, dc['y'] + dc['h'] * fr_d
            edge['style'] = style + f"exitX={1 if sc_col == 0 else 0};exitY={fr_s};entryX={1 if dc_col == 0 else 0};entryY={fr_d};"
            edge['points'] = [{'x': lx_track, 'y': sy_}, {'x': lx_track, 'y': dy_}]
            if sy_ == dy_:
                edge['off'] = (0, -11)   # a straight run: the label above it, not on it
            sx_edge = sc['x'] + sc['w'] if sc_col == 0 else sc['x']
            dx_edge = dc['x'] + dc['w'] if dc_col == 0 else dc['x']
            h1, v, h2 = abs(lx_track - sx_edge), abs(dy_ - sy_), abs(lx_track - dx_edge)
            if v:
                edge['lx'] = round(2 * ((h1 + 0.5 * v) / (h1 + v + h2)) - 1, 3)
        elif is_actor(a['from']) and a['to'] in compute:
            # own x track per actor line, own height at the compute icon: no shared or crossing runs
            gx = gx_of[(a['from'], a['to'])]
            sib = at_comp[a['to']]
            fr = 0.2 + (0.6 * sib.index(a) / (len(sib) - 1) if len(sib) > 1 else 0.3)
            edge['style'] = style + f"exitX=1;exitY=0.5;entryX=0;entryY={num(round(fr, 2))};"
            edge['points'] = [{'x': gx, 'y': sc['y'] + sc['h'] / 2}, {'x': gx, 'y': dc['y'] + dc['h'] * fr}]
        elif is_actor(a['to']) and a['from'] in compute:
            gx = gx_of[(a['from'], a['to'])]
            sib = at_comp[a['from']]
            fr = 0.2 + (0.6 * sib.index(a) / (len(sib) - 1) if len(sib) > 1 else 0.7)
            edge['style'] = style + f"exitX=0;exitY={num(round(fr, 2))};entryX=1;entryY=0.5;"
            edge['points'] = [{'x': gx, 'y': sc['y'] + sc['h'] * fr}, {'x': gx, 'y': dc['y'] + dc['h'] / 2}]
        elif is_actor(a['to']):
            # Outbound to an external service: out of the left side towards the external zone.
            # Up over the row and out along the subnet's left edge, so the line does not
            # run through the icons to the left of its source.
            edge['style'] = style + 'exitX=0.5;exitY=0;entryX=1;entryY=0.5;'
            left = by_id[sc['parent']]['x'] + 10 if sc['parent'] in by_id else sc['slot']['x']
            edge['points'] = [{'x': sc['x'] + sc['w'] / 2, 'y': sc['slot']['y'] + 3}, {'x': left, 'y': sc['slot']['y'] + 3}]
        elif a['from'] in paas and a['to'] in paas and abs(paas.index(a['from']) - paas.index(a['to'])) > 1:
            # Not neighbours: draw.io's own route went through every icon in between. Up out of
            # the source, along the strip above the row's icons, down beside the target, in at the
            # side that faces the source. The label sits above the run.
            to_right = dc['x'] > sc['x']
            top_y = min(sc['slot']['y'], dc['slot']['y']) - 6
            x_side = (dc['x'] - 12) if to_right else (dc['x'] + dc['w'] + 12)
            edge['style'] = style + f"exitX={0.8 if to_right else 0.2};exitY=0;entryX={0 if to_right else 1};entryY=0.5;"
            edge['points'] = [{'x': sc['x'] + sc['w'] * (0.8 if to_right else 0.2), 'y': top_y}, {'x': x_side, 'y': top_y}, {'x': x_side, 'y': dc['y'] + dc['h'] / 2}]
            # the label beside the descent at the target, where no other label sits (the strip
            # above the row carries the trunk labels)
            v1, h, v2 = abs(sc['y'] - top_y), abs(x_side - sc['x'] - sc['w'] * (0.8 if to_right else 0.2)), abs(dc['y'] + dc['h'] / 2 - top_y)
            if v1 + h + v2 and edge_label:
                edge['lx'] = round(2 * ((v1 + h + 0.5 * v2) / (v1 + h + v2 + 12)) - 1, 3)
                edge['off'] = ((-1 if to_right else 1) * (8 + 3 * plain_len(edge_label)), 0)
        else:
            edge['style'] = style + 'exitX=1;exitY=0.5;entryX=0;entryY=0.5;'
            if edge_label:
                edge['off'] = (0, -11)   # a short direct line: the label above it, clear of the arrowhead
        if a in actor_edges and edge.get('points') and len(edge['points']) == 2 and edge_label:
            # Label above the horizontal run at the compute icon - the only segment that is this
            # line's own; the vertical in the gap is where the other actor lines run.
            p0, p1 = edge['points']
            sx_, sy_ = (sc['x'] + sc['w'], sc['y'] + sc['h'] / 2) if is_actor(a['from']) else (sc['x'], p0['y'])
            ex_, ey_ = (dc['x'], p1['y']) if is_actor(a['from']) else (dc['x'] + dc['w'], dc['y'] + dc['h'] / 2)
            h1, v, h2 = abs(p0['x'] - sx_), abs(p1['y'] - p0['y']), abs(ex_ - p1['x'])
            tot = h1 + v + h2
            if tot:
                f = (h1 + v + 0.5 * h2) / tot if is_actor(a['from']) else (0.5 * h1) / tot
                edge['lx'] = round(2 * f - 1, 3)
                edge['off'] = (0, -11)
        edges.append(edge)

    # Hub layout: one line per caller into the endpoints, one per service out of them.
    #   - A caller's track: the farther a caller is from the endpoints' height, the further right
    #     its track, so a vertical never crosses another caller's run on its way in.
    #   - A caller enters the endpoints at its own height, in the order the callers sit.
    #   - All service lines leave on one trunk, outside the network.
    if side and 'pe-bundle' in by_id and 'snet-pe' in by_id:
        pe = by_id['pe-bundle']
        cx0 = by_id['snet-pe']['x'] - coll_w
        pe_mid = pe['y'] + pe['h'] / 2
        n_c = len(callers)
        out_fr = {k: (OUT_FR if k in inter_tgt else 0.5) for k in callers}
        mid_y = {k: by_id[node_of[k]]['y'] + by_id[node_of[k]]['h'] * out_fr[k] for k in callers if node_of[k] in by_id}
        by_dist = sorted(mid_y, key=lambda k: -abs(mid_y[k] - pe_mid))
        by_y = sorted(mid_y, key=lambda k: mid_y[k])
        for k in by_y:
            tx = cx0 + 14 + TRK * (n_c - 1 - by_dist.index(k))
            frac = 0.2 + (0.6 * by_y.index(k) / (n_c - 1) if n_c > 1 else 0.3)
            public = any(is_public_edge(a) for a in access if a['from'] == k and a['to'] in paas)
            color = PUBLIC_COLOR if public else (caller_color[k] if dense else PRIVATE_COLOR)
            st = EDGE_BASE + f"strokeColor={color};exitX=1;exitY={out_fr[k]};entryX=0;entryY={num(frac)};"
            edges.append({'id': f"e-in-{by_y.index(k)}", 'source': node_of[k], 'target': 'pe-bundle', 'value': '', 'style': st,
                          'points': [{'x': tx, 'y': mid_y[k]}, {'x': tx, 'y': pe['y'] + pe['h'] * frac}]})
        trunk = vn_cell['x'] + vn_cell['w'] + 28
        for i, k in enumerate(paas):
            if k not in callers_of or f"res-{k}" not in by_id:
                continue
            dc = by_id[f"res-{k}"]
            if i % cols_p == 0:
                # first column: in from the left at the icon's height - lower (0.3) when a
                # PaaS -> PaaS line leaves the icon at 0.7 on the other side
                fr = 0.3 if k in pp_touched else 0.5
                st = EDGE_BASE + f"strokeColor={PRIVATE_COLOR};exitX=1;exitY=0.5;entryX=0;entryY={fr};"
                pts = [{'x': trunk, 'y': pe_mid}, {'x': trunk, 'y': dc['y'] + dc['h'] * fr}]
            else:
                # second column: along the gutter above its row, past the first column's slot, and
                # down into the icon from the top
                gy = dc['slot']['y'] - GUT / 2
                st = EDGE_BASE + f"strokeColor={PRIVATE_COLOR};exitX=1;exitY=0.5;entryX=0.5;entryY=0;"
                pts = [{'x': trunk, 'y': pe_mid}, {'x': trunk, 'y': gy}, {'x': dc['x'] + dc['w'] / 2, 'y': gy}]
            edges.append({'id': f"e-out-{i}", 'source': 'pe-bundle', 'target': f"res-{k}", 'value': '', 'style': st, 'points': pts})

    # Legend: only what the picture uses.
    legend = [f"<b>{esc(T['legend'])}</b>"]
    if dense:
        legend.append(f"<i>{esc(T['legCallers'])}</i>")
        for k in by_top:
            legend.append(f"<font color='{caller_color[k]}'><b>&#9473;&#9473;&#9654;</b></font> "
                          f"{esc(TYPE_NAMES.get(base(k), base(k)))} &#183; {esc(s(purposes.get(k)) or (k.partition('__')[2] or k))}")
    if side:
        # one blue row: the endpoint lines alone, or every private line when other blue lines
        # (users reaching the app, telemetry) exist too - two rows with one arrow said nothing
        other_blue = any(PRIVATE_COLOR in e['style'] and not e['id'].startswith('e-out-') for e in edges)
        legend.append(f"<font color='{PRIVATE_COLOR}'><b>&#9473;&#9473;&#9654;</b></font> {esc(T['legPrivateAny'] if other_blue else T['legPE'])}")
    elif not dense and any(PRIVATE_COLOR in e['style'] for e in edges):
        legend.append(f"<font color='{PRIVATE_COLOR}'><b>&#9473;&#9473;&#9654;</b></font> {esc(T['legPrivate'])}")
    if any(PUBLIC_COLOR in e['style'] for e in edges):
        legend.append(f"<font color='{PUBLIC_COLOR}'><b>&#9473;&#9473;&#9654;</b></font> {esc(T['legPublic'])}")
    if vnet_existing or law_existing or ((zones or dns_ownership) and dns_existing):
        legend.append(f"<font color='#999999'>&#9477;&#9477;&#9477;</font> {esc(T['legExisting'])}")
    if optional:
        legend.append(f"<font color='#999999'>&#9679;</font> {esc(T['legOptional'])}")
    if open_items or assumed:
        # open items are drawn as red text (a flagged label, the panel list), not as a marker
        legend.append(f"<font color='#D13438'>{esc(T['legOpen'])}</font>")
    if len(legend) > 1:
        add_container({'id': 'legend', 'parent': '1', 'x': sub_x, 'y': legend_y, 'w': min(max(sub_w, 420), 560), 'h': len(legend) * 15 + 26,
                       'style': 'rounded=1;arcSize=4;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacing=10;fillColor=#FFFFFF;strokeColor=#C8C6C4;fontSize=11;',
                       'value': '<br>'.join(legend)})

    # Decisions panel, under the legend across the group's width, in up to three columns filled
    # to equal height and broken only between lines - never beside the group, which would widen
    # a page that should fit A4 landscape. The first column keeps the id `panel`.
    lines = [f"<b>{T['decisions']}</b>"]
    if exposure:
        lines.append(f"{T['exposure']}: <b>{esc(exposure)}</b>")
    if net_ownership:
        lines.append(f"{T['network']}: {esc(net_ownership)}" + (f", {esc(vn_sub)}" if vn_sub else ''))
    mand = [m for m in as_list(get_decision(dep, ['mandates'])) if m]
    if mand:
        lines.append(f"{T['mandates']}: {esc(', '.join(s(m) for m in mand))}")
    if dns_ownership:
        lines.append(f"{T['dns']}: {esc(dns_ownership)}")
    if diag_target:
        lines.append(f"{T['diag']}: {esc(diag_target)}" + (f" ({esc(diag_ref['rg'])})" if diag_ref['rg'] else ''))
    if vnet_existing and vnet_ref['rg']:
        lines.append(f"VNet: {esc(vnet_ref['name'])} ({esc(vnet_ref['rg'])})")
    # Nothing that is prose. The forced chains, the questions and their reasons are in the
    # decision document beside the spec; the picture counts what stays open and who owns it, and
    # the affected resources are drawn red (owner's call, 2026-10-24: a drawing is not where
    # prose is read).
    if open_items or assumed:
        lines.append('')
        if open_items:
            owners = {}
            for o in open_items:
                who = s(o.get('owner')) if isinstance(o, dict) and o.get('owner') else T['noOwner']
                owners[who] = owners.get(who, 0) + 1
            by_owner = ', '.join(f"{esc(w)} ×{n}" if n > 1 else esc(w) for w, n in owners.items())
            lines.append(f"<font color='#D13438'><b>{T['open']}: {len(open_items)}</b> &#183; {by_owner}</font>")
        if assumed:
            lines.append(f"<font color='#D13438'><b>{T['assumed']}: {len(assumed)}</b></font>")
        lines.append(f"<i>{esc(T['openRef'])}</i>")
    PANEL_STYLE = 'rounded=1;arcSize=3;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacing=12;fillColor=#F3F2F1;strokeColor=#C8C6C4;'

    def wrapped(text_lines, width):
        # Wrap estimate measured on the export: ~54 characters per line at 12px in 340px, 15px a line.
        return sum(max(1, math.ceil(plain_len(line) / max(int((width - 24) / 5.6), 20))) for line in text_lines)
    legend_cell = next((c for c in containers if c['id'] == 'legend'), None)
    beside = legend_cell is not None and sub_w - legend_cell['w'] - 20 >= 380
    if beside:
        # right of the legend, in the width that is left
        px0, py, avail = legend_cell['x'] + legend_cell['w'] + 20, legend_y, sub_w - legend_cell['w'] - 20
    else:
        px0, py, avail = sub_x, (legend_cell['y'] + legend_cell['h'] + 20) if legend_cell else legend_y, sub_w
    n_col = max(1, min(3, int(avail // 400)))
    col_w = (avail - 20 * (n_col - 1)) / n_col
    heights = [wrapped([line], col_w) for line in lines]

    def chunks(cap):
        out, acc = [[]], 0
        for line, h in zip(lines, heights):
            if out[-1] and acc + h > cap:
                out.append([])
                acc = 0
            out[-1].append(line)
            acc += h
        return out
    # the smallest column height that still fits the list into n_col columns
    lo, hi = max(heights), sum(heights)
    while lo < hi:
        mid = (lo + hi) // 2
        if len(chunks(mid)) <= n_col:
            hi = mid
        else:
            lo = mid + 1
    cols = chunks(lo)
    tall = max(wrapped(c, col_w) for c in cols) * 15 + 30
    for j, c in enumerate(cols):
        add_container({'id': 'panel' if j == 0 else f"panel-{j}", 'parent': '1', 'x': px0 + j * (col_w + 20), 'y': py,
                       'w': col_w, 'h': tall, 'style': PANEL_STYLE, 'value': '<br>'.join(c)})

    # Containers first, then icons, so icons are drawn on top.
    cells = containers + icons
    by_id = {c['id']: c for c in cells}

    # --- Overlap check -----------------------------------------------------
    # Siblings must not overlap. An icon is checked by its slot (icon + label), not
    # by its 48px image, since the label is what collides first.
    def box(c):
        return c['slot'] if c.get('slot') else {'x': c['x'], 'y': c['y'], 'w': c['w'], 'h': c['h']}

    problems = []
    by_parent = {}
    for c in cells:
        if c['id'].endswith('-icon') or c['id'] in ('rg-private', 'diag-note'):
            continue
        by_parent.setdefault(c['parent'], []).append(c)
    for group in by_parent.values():
        for a in range(len(group)):
            for b in range(a + 1, len(group)):
                p, q = box(group[a]), box(group[b])
                if p['x'] < q['x'] + q['w'] and q['x'] < p['x'] + p['w'] and p['y'] < q['y'] + q['h'] and q['y'] < p['y'] + p['h']:
                    problems.append(f"{group[a]['id']} overlaps {group[b]['id']}")
    # A label below an icon must end inside its slot. Estimated: ~26 characters
    # per line at the slot's label width, 16px per line.
    for c in cells:
        if not c.get('labelBelow'):
            continue
        if c['y'] + c['h'] + 4 + label_lines(c['value']) * 16 > c['slot']['y'] + c['slot']['h']:
            problems.append(f"{c['id']}: label of {label_lines(c['value'])} lines does not fit its slot")
    # Children must fit inside their container.
    for c in cells:
        if c['parent'] == '1':
            continue
        p, b = by_id[c['parent']], box(c)
        if b['x'] < p['x'] or b['y'] < p['y'] or b['x'] + b['w'] > p['x'] + p['w'] or b['y'] + b['h'] > p['y'] + p['h']:
            problems.append(f"{c['id']} leaves its container {c['parent']}")
    if problems:
        for p in problems:
            say(f"[fail] {p}", 'red')
        return 1

    # --- Emit --------------------------------------------------------------
    diagram_name = get_at(spec, ['spec', 'id'])
    o = []
    o.append('<mxfile host="infrastructure-as-skills-azure">')
    o.append(f'  <diagram id="infra" name="{esc(diagram_name if diagram_name is not None else "infra")}">')
    o.append('    <mxGraphModel grid="1" gridSize="10" page="0" math="0" shadow="0">')
    o.append('      <root>')
    o.append('        <mxCell id="0"/>')
    o.append('        <mxCell id="1" parent="0"/>')
    for c in cells:
        px = py = 0
        if c['parent'] != '1':
            px, py = by_id[c['parent']]['x'], by_id[c['parent']]['y']
        o.append(f'        <mxCell id="{c["id"]}" value="{esc(c["value"])}" style="{esc(c["style"])}" vertex="1" parent="{c["parent"]}">')
        o.append(f'          <mxGeometry x="{num(c["x"] - px)}" y="{num(c["y"] - py)}" width="{num(c["w"])}" height="{num(c["h"])}" as="geometry"/>')
        o.append('        </mxCell>')
    for e in edges:
        o.append(f'        <mxCell id="{e["id"]}" value="{esc(e["value"])}" style="{esc(e["style"])}" edge="1" parent="1" source="{e["source"]}" target="{e["target"]}">')
        lx_attr = ' x="' + num(e['lx']) + '"' if 'lx' in e else ''
        inner = ''
        if e.get('points'):
            # Waypoints are absolute, since every edge's parent is the root layer.
            inner += '<Array as="points">' + ''.join(f'<mxPoint x="{num(p["x"])}" y="{num(p["y"])}"/>' for p in e['points']) + '</Array>'
        if e.get('off'):
            inner += f'<mxPoint x="{num(e["off"][0])}" y="{num(e["off"][1])}" as="offset"/>'
        if inner:
            o.append(f'          <mxGeometry{lx_attr} relative="1" as="geometry">{inner}</mxGeometry>')
        else:
            o.append(f'          <mxGeometry{lx_attr} relative="1" as="geometry"/>')
        o.append('        </mxCell>')
    o.append('      </root>')
    o.append('    </mxGraphModel>')
    o.append('  </diagram>')
    o.append('</mxfile>')

    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(o) + '\n')
    say(f"[ ok ] {out} - {len(cells)} shapes, {len(edges)} edges, no overlaps", 'green')
    return 0


if __name__ == '__main__':
    sys.exit(main())
