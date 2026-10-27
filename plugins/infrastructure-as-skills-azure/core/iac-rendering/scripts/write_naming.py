#!/usr/bin/env python3
"""Writes the root's naming.yaml beside an infra-spec.yaml when it has none.

    python write_naming.py <infra-spec.yaml> [--check]

Every root carries a full copy of the convention (references/naming.md): the targets read
that copy, never the plugin's default, so a default that moves renames nothing deployed.
The copy is references/naming.default.yaml as it is, comments included - except where a
Bicep root already names resources: each name `var` in the root's *.bicep is read back into
a pattern, and where it differs from what the current default gives its type, the copy
carries the root's pattern. An existing naming.yaml is never touched.

A name var is read when it is a single quoted template (optionally inside toLower()) that
starts with a type abbreviation and holds only the name tokens:
`${loc}` <LOCATION>, `${env}` <ENVIRONMENT>, `${workload}` <NAME>, `${idx}` <INDEX>,
`${uidN}` / `${take(uniqueString(...), N)}` <UNIQUE_ID_N>, with `-` or nothing between them.
Anything else - a literal sub-name, an unknown token, an abbreviation two types share with
different patterns - is reported and left to the default.

Nothing is written for a Terraform root whose deployment.naming_source is `module` or
`custom`: the names come from somewhere else there.

Exit 0 written or already present (or not needed), 1 --check found it missing, 2 not written.
Needs PyYAML.
"""
import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML is required: pip install pyyaml")
    sys.exit(2)

HERE = Path(__file__).resolve().parent
DEFAULT = HERE.parent / "references" / "naming.default.yaml"

VAR = re.compile(r"^\s*var\s+(\w+)\s*=\s*(?:toLower\()?'([^']*)'\)?\s*(?://.*)?$")
TOKENS = [
    (re.compile(r"\$\{loc\}"), "<LOCATION>"),
    (re.compile(r"\$\{env\}"), "<ENVIRONMENT>"),
    (re.compile(r"\$\{workload\}"), "<NAME>"),
    (re.compile(r"\$\{idx\}"), "<INDEX;%02s>"),
    (re.compile(r"\$\{uid(\d+)\}"), r"<UNIQUE_ID_\1>"),
    (re.compile(r"\$\{take\(uniqueString\([^)]*\),\s*(\d+)\)\}"), r"<UNIQUE_ID_\1>"),
]
PATTERN = re.compile(r"^(?:-?<(?:LOCATION|ENVIRONMENT|NAME|INDEX;%02s|UNIQUE_ID_\d+)>)+$")


def value(node):
    return node.get("value") if isinstance(node, dict) else node


def read_pattern(template):
    """'kv-${env}-${workload}-${uid4}' -> ('kv', '<TYPE>-<ENVIRONMENT>-<NAME>-<UNIQUE_ID_4>'), else None."""
    m = re.match(r"^([a-z0-9]+)(?=-|\$\{)", template)
    if not m:
        return None
    rest = template[m.end():]
    for rx, token in TOKENS:
        rest = rx.sub(token, rest)
    if not PATTERN.match(rest):
        return None
    return m.group(1), "<TYPE>" + rest


def normal(pattern):
    """Compares patterns as names: an optional part left empty, the index format implied."""
    p = re.sub(r"<\?[^>]*>", "", pattern)
    return re.sub(r"<INDEX(?:;[^>]*)?>", "<INDEX>", p)


def pins(root, convention):
    """-> ({type: pattern}, [notes]) for every name var whose pattern differs from the default."""
    azure = convention.get("patterns", {}).get("Azure", {})
    by_abbr = {}
    for key, abbr in (convention.get("abbreviations", {}).get("Azure") or {}).items():
        by_abbr.setdefault(str(abbr), set()).add(key.split("::")[0])

    def effective(rtype):
        block = azure.get(rtype)
        return block.get("default") if isinstance(block, dict) and block.get("default") else azure.get("default", "")

    found, notes = {}, []
    for bicep in sorted(root.rglob("*.bicep")):
        for line in bicep.read_text(encoding="utf-8").splitlines():
            m = VAR.match(line)
            if not m or not m.group(1).endswith("Name"):
                continue
            read = read_pattern(m.group(2))
            if read is None:
                notes.append(f"{bicep.name}: {m.group(1)} not read back ('{m.group(2)}'), the default stays")
                continue
            abbr, pattern = read
            types = sorted(by_abbr.get(abbr, ()))
            if not types:
                notes.append(f"{bicep.name}: {m.group(1)} - no type has the abbreviation '{abbr}'")
                continue
            differs = [t for t in types if normal(effective(t)) != normal(pattern)]
            if not differs:
                continue
            if len(types) > 1:
                notes.append(f"{bicep.name}: {m.group(1)} - '{abbr}' is {', '.join(types)}; not pinned, decide by hand")
                continue
            if found.get(types[0], pattern) != pattern:
                notes.append(f"{bicep.name}: {m.group(1)} - {types[0]} named two ways; the first is kept")
                continue
            found[types[0]] = pattern
    return found, notes


def apply(text, found):
    """The default's text with each pinned type's pattern - its block replaced, or one added."""
    for rtype, pattern in sorted(found.items()):
        line = f'      default: "{pattern}"'
        note = "      # Pinned: the root names it so (rendered from an older default)."
        block = re.compile(rf'^(    {re.escape(rtype)}:\n)      default: "[^"\n]*"$', re.M)
        if block.search(text):
            text = block.sub(lambda m: m.group(1) + note + "\n" + line, text, count=1)
            continue
        anchor = re.compile(r'^(  Azure:\n    default: "[^"\n]*"\n)', re.M)
        if not anchor.search(text):
            raise ValueError("patterns.Azure.default not found in the convention")
        text = anchor.sub(lambda m: m.group(1) + f"\n    {rtype}:\n{note}\n{line}\n", text, count=1)
    return text


def main():
    ap = argparse.ArgumentParser(description="Write the root's naming.yaml beside an infra-spec.yaml when it has none.")
    ap.add_argument("spec", help="the infra-spec.yaml")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 when naming.yaml is missing")
    args = ap.parse_args()

    spec_path = Path(args.spec)
    if not spec_path.is_file():
        print(f"no such file: {spec_path}")
        return 2
    target = spec_path.with_name("naming.yaml")
    if target.exists():
        print(f"{target}: present, left as it is")
        return 0
    try:
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        print(f"{spec_path}: YAML does not parse: {e}")
        return 2
    tgt = str((spec.get("spec") or {}).get("target", ""))
    source = value((spec.get("deployment") or {}).get("naming_source"))
    if tgt == "terraform" and source in ("module", "custom"):
        print(f"{spec_path}: naming_source {source} - no naming.yaml")
        return 0
    if args.check:
        print(f"{target}: missing - run write_naming.py on the spec")
        return 1

    text = DEFAULT.read_text(encoding="utf-8")
    found, notes = pins(spec_path.parent, yaml.safe_load(text)) if tgt == "bicep" else ({}, [])
    try:
        new = apply(text, found)
    except ValueError as e:
        print(f"{target}: not written - {e}")
        return 2
    azure = yaml.safe_load(new)["patterns"]["Azure"]
    if any(azure.get(t, {}).get("default") != p for t, p in found.items()):
        print(f"{target}: not written - a pinned pattern did not land")
        return 2
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    print(f"{target}: written, a full copy of the convention"
          + (f", {len(found)} pattern(s) pinned: " + ", ".join(f"{t} {p}" for t, p in sorted(found.items())) if found else ""))
    for n in notes:
        print(f"  note: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
