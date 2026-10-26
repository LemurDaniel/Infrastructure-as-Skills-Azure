#!/usr/bin/env python3
"""Lists the names a spec's resources will get - offline, from the spec and the convention.

No Terraform, no Azure CLI, no login: the name is the type's pattern from
references/naming.default.yaml (or the `naming.yaml` beside the spec) with the tokens filled
from the spec. It is a best guess, and says so. What it cannot know is marked - `<UNIQUE_ID_n>` is printed as `?`, a
global name is never reported free, and what a module names inside itself is not listed.

    python list_names.py <infra-spec.yaml> [--stage production] [--naming naming.yaml]
                         [--language en|de]

Exit 1 when a name breaks its type's length or character rule, or when two resources get
the same name. Needs PyYAML.
"""
import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
DEFAULT_NAMING = HERE.parent / "references" / "naming.default.yaml"

# type id -> (min, max, charset regex of the whole name, must start with a letter, global)
# Global = unique across Azure (a DNS name); otherwise unique in its scope only.
LIMITS = {
    "Microsoft.Storage/storageAccounts": (3, 24, r"[a-z0-9]+", False, True),
    "Microsoft.KeyVault/vaults": (3, 24, r"[a-zA-Z0-9-]+", True, True),
    "Microsoft.ContainerRegistry/registries": (5, 50, r"[a-zA-Z0-9]+", False, True),
    "Microsoft.DocumentDB/databaseAccounts": (3, 44, r"[a-z0-9-]+", False, True),
    "Microsoft.Search/searchServices": (2, 60, r"[a-z0-9-]+", False, True),
    "Microsoft.CognitiveServices/accounts": (2, 64, r"[a-zA-Z0-9-]+", False, True),
    "Microsoft.Web/sites": (2, 60, r"[a-zA-Z0-9-]+", False, True),
    "Microsoft.App/containerApps": (2, 32, r"[a-z0-9-]+", True, False),
    "Microsoft.Network/virtualNetworks": (2, 64, r"[a-zA-Z0-9._-]+", False, False),
    "Microsoft.Network/networkSecurityGroups": (1, 80, r"[a-zA-Z0-9._-]+", False, False),
    "Microsoft.OperationalInsights/workspaces": (4, 63, r"[a-zA-Z0-9-]+", False, False),
    "Microsoft.Insights/components": (1, 260, r"[^<>%&:\\?/]+", False, False),
    "Microsoft.ManagedIdentity/userAssignedIdentities": (3, 128, r"[a-zA-Z0-9_-]+", False, False),
    "Microsoft.Resources/resourceGroups": (1, 90, r"[\w.()-]+", False, False),
}

TEXT = {
    "en": {
        "stage": "Stage", "resource": "Resource", "name": "Name", "action": "Action",
        "note": "Note", "create": "create", "existing": "existing (not created)",
        "stated": "stated", "global": "global name, availability unchecked",
        "unique": "id from seed, final value unknown", "len": "{n} chars, allowed {lo}-{hi}",
        "chars": "characters not allowed", "letter": "must start with a letter",
        "dup": "same name as {other}: two instances need different names",
        "foot": "Derived from the spec and the convention, a best guess. Not listed: private endpoints, diagnostic settings, role "
                "assignments, names a module builds inside itself.",
        "nopattern": "no question set - not listed",
    },
    "de": {
        "stage": "Stage", "resource": "Ressource", "name": "Name", "action": "Aktion",
        "note": "Hinweis", "create": "anlegen", "existing": "vorhanden (nicht angelegt)",
        "stated": "vorgegeben", "global": "globaler Name, Verfügbarkeit ungeprüft",
        "unique": "Id aus Seed, Endwert unbekannt", "len": "{n} Zeichen, erlaubt {lo}-{hi}",
        "chars": "Zeichen nicht erlaubt", "letter": "muss mit einem Buchstaben beginnen",
        "dup": "gleicher Name wie {other}: zwei Instanzen brauchen verschiedene Namen",
        "foot": "Aus Spec und Convention abgeleitet, ein Best Guess. "
                "Nicht aufgeführt: Private Endpoints, Diagnoseeinstellungen, Rollenzuweisungen, "
                "Namen, die ein Modul intern bildet.",
        "nopattern": "kein Question-Set - nicht aufgeführt",
    },
}


def merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            merge(base[k], v)
        else:
            base[k] = v
    return base


def load_yaml(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def value(node):
    """A spec entry is {value, source}; a stage map or a plain value comes through as is."""
    return node["value"] if isinstance(node, dict) and "value" in node else node


def per_stage(node, stage):
    node = value(node)
    if isinstance(node, dict):
        return node.get(stage)
    return node


def find_set(name):
    hits = sorted((PLUGIN / "resources").glob(f"*/{name}/questions.yaml"))
    return load_yaml(hits[0]) if hits else None


TOKEN = re.compile(r"<(\?)?([A-Z_]+?)(?:_(\d+))?(?:;([^>]*))?>")


def render(pattern, parts, abbreviation, index_modifier):
    """Fills one pattern. Returns (name, has_unique_id)."""
    unique = False

    def fill(m):
        nonlocal unique
        optional, token, n, fmt = m.groups()
        if token == "UNIQUE_ID":
            unique = True
            return "?" * int(n or 4)
        if token == "TYPE":
            return abbreviation
        if token == "INDEX":
            return (fmt or "%s").replace("%02s", f"{index_modifier:02d}").replace("%s", str(index_modifier))
        val = parts.get(token, "")
        if not val:
            return ""
        return (fmt or "%s").replace("%s", val)

    return TOKEN.sub(fill, pattern), unique


def check(type_id, name):
    """Returns a list of text keys for the rules the name breaks."""
    limits = LIMITS.get(type_id)
    if not limits:
        return []
    lo, hi, charset, letter, _ = limits
    bad = []
    if not lo <= len(name) <= hi:
        bad.append(("len", {"n": len(name), "lo": lo, "hi": hi}))
    if not re.fullmatch(charset, name.replace("?", "a")):
        bad.append(("chars", {}))
    if letter and not name[:1].isalpha():
        bad.append(("letter", {}))
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--stage", help="one stage; default: every stage in context.environments")
    ap.add_argument("--naming", help="naming.yaml merged over the default; default: the one beside the spec")
    ap.add_argument("--language", choices=sorted(TEXT))
    args = ap.parse_args()

    spec_path = Path(args.spec)
    spec = load_yaml(spec_path)
    ctx, dep = spec.get("context", {}), spec.get("deployment", {})
    lang = args.language or ctx.get("language", "en")
    t = TEXT.get(lang, TEXT["en"])

    conv = load_yaml(DEFAULT_NAMING)
    custom = Path(args.naming) if args.naming else spec_path.with_name("naming.yaml")
    if custom.is_file():
        merge(conv, load_yaml(custom))
    modifier = int(conv.get("index_modifier", 1))
    patterns = conv["patterns"]["Azure"]
    abbreviations = conv["abbreviations"]["Azure"]
    loc_map, env_map = conv["mappings"]["location"], conv["mappings"]["environment"]

    stages = [args.stage] if args.stage else (ctx.get("environments") or ["production"])
    location, workload = ctx.get("location", ""), ctx.get("workload", "")
    if location not in loc_map:
        sys.exit(f"location '{location}' is not in mappings.location of the convention")

    failed = False
    for stage in stages:
        if stage not in env_map:
            sys.exit(f"stage '{stage}' is not in mappings.environment of the convention")
        base = {"LOCATION": loc_map[location], "ENVIRONMENT": env_map[stage], "NAME": workload}
        rows = []  # (resource, type_id, name, action, notes[])

        def add(resource, type_id, abbr, extra, action, fixed=None):
            parts = dict(base, **extra)
            if fixed:
                name, uniq = fixed, False
            else:
                pattern = (patterns.get(type_id) or {}).get("default") or patterns["default"]
                name, uniq = render(pattern, parts, abbr, modifier)
            name = name.lower()
            notes = [t["stated"]] if fixed else []
            if uniq:
                notes.append(t["unique"])
            if LIMITS.get(type_id, (0, 0, "", 0, False))[4] and action == t["create"]:
                notes.append(t["global"])
            rows.append([resource, type_id, name, action, notes, check(type_id, name)])

        # Resource groups: the main group and the split roles; a split (resource_group_layout:
        # split) has no main group.
        split = value(dep.get("resource_group_split")) or []
        has_main = value(dep.get("resource_group_layout")) != "split"
        for role in (["main"] if has_main else []) + list(split):
            key = "resource_group_name" + ("" if role == "main" else f"_{role}")
            mode = value(dep.get(f"resource_group_mode_{role}")) or "existing"
            stated = per_stage(ctx.get(key), stage)
            action = t["create"] if mode == "create" else t["existing"]
            if stated:
                add(f"resource group ({role})", "Microsoft.Resources/resourceGroups", "rg", {}, action, fixed=stated)
            elif mode == "create":
                extra = {} if role == "main" else {"NAME": f"{workload}-{role}"}
                add(f"resource group ({role})", "Microsoft.Resources/resourceGroups", "rg", extra, action)

        for key in (spec.get("resources") or {}):
            set_name, _, instance = key.partition("__")
            qs = find_set(set_name)
            naming = (qs or {}).get("naming", {})
            terraform_id = naming.get("terraform", "")
            if not terraform_id:
                continue
            type_id = terraform_id.removeprefix("Azure::").split("::")[0]
            abbr = naming.get("abbreviation") or abbreviations.get(f"{type_id}::default", "")
            # An instance joins the workload in <NAME>; <SUBNAME> is for sub-resources.
            add(key, type_id, abbr, {"NAME": workload + instance} if instance else {}, t["create"])
            # Subnets are named by the spec, verbatim.
            if set_name == "virtual-network":
                subnets = per_stage(spec["resources"][key].get("addressing", {}).get("subnets"), stage) or []
                for sn in subnets:
                    if isinstance(sn, dict) and sn.get("name"):
                        add(f"  subnet", "Microsoft.Network/virtualNetworks/subnets", "snet", {}, t["create"], fixed=sn["name"])

        # Two resources of one scope with one name: the pattern lacks what tells them apart.
        seen = {}
        for r in rows:
            k = (r[1], r[2])
            if k in seen:
                r[5].append(("dup", {"other": seen[k]}))
            else:
                seen[k] = r[0]

        print(f"\n### {t['stage']}: {stage}\n")
        print(f"| {t['resource']} | {t['name']} | {t['action']} | {t['note']} |")
        print("|---|---|---|---|")
        for resource, type_id, name, action, notes, errors in rows:
            texts = list(notes)
            for k, kw in errors:
                texts.append("**" + t[k].format(**kw) + "**")
                failed = True
            print(f"| {resource} | `{name}` | {action} | {'; '.join(texts)} |")

    print(f"\n_{t['foot']}_")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
