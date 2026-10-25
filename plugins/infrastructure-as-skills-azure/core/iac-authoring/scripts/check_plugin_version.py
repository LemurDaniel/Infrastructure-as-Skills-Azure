#!/usr/bin/env python3
"""Compares the plugin installed here with the one that last wrote a spec.

    python check_plugin_version.py <infra-spec.yaml>

Exit 0: the installed plugin is the same or newer than `spec.plugin_version`, or the spec
carries none (written before the field existed) or an unreadable one - never a reason to
stop. Exit 3: the spec was written by a NEWER plugin than this one; the caller halts, asks
the person to update and renders nothing. Any other exit is an error of the script itself.
Needs PyYAML.
"""
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

PLUGIN_JSON = Path(__file__).resolve().parents[3] / ".claude-plugin" / "plugin.json"
NEWER = 3


def parse(v):
    """'0.0.3' or '0.1.0-beta' -> (0, 0, 3); anything else -> None."""
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", str(v).strip()) if v is not None else None
    return tuple(int(g) for g in m.groups()) if m else None


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    installed = json.loads(PLUGIN_JSON.read_text(encoding="utf-8")).get("version")
    spec = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8")) or {}
    head = spec.get("spec") if isinstance(spec, dict) else None
    recorded = head.get("plugin_version") if isinstance(head, dict) else None

    have, was = parse(installed), parse(recorded)
    if have is None:
        sys.exit(f"{PLUGIN_JSON}: no readable version ({installed!r})")
    if recorded is None:
        print(f"installed={installed} spec=none: the spec predates plugin_version; stamp it when it is written next.")
        return 0
    if was is None:
        print(f"installed={installed} spec={recorded!r}: not a version, ignored; stamp it when it is written next.")
        return 0
    if was > have:
        print(f"installed={installed} spec={recorded}: the spec was written by a newer plugin - halt and ask for an update.")
        return NEWER
    print(f"installed={installed} spec={recorded}: ok" + ("" if was == have else "; stamp the spec with the installed version when it is written next."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
