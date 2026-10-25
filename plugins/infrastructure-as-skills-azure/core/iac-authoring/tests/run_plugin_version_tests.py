#!/usr/bin/env python3
"""Tests check_plugin_version.py: only a spec from a NEWER plugin stops a run (exit 3).

    python run_plugin_version_tests.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_plugin_version.py"
INSTALLED = json.loads((SCRIPT.parents[3] / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
MAJOR, MINOR, PATCH = (int(p) for p in INSTALLED.split("-")[0].split("."))


def run(head):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "infra-spec.yaml"
        path.write_text(yaml.safe_dump({"schema_version": 1, "spec": head}), encoding="utf-8")
        p = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def case(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL ") + name + ("" if ok else f"\n{detail}"))
    return ok


def main():
    results = []
    for name, version, expected in (
        ("same version: ok", INSTALLED, 0),
        ("older spec: ok", f"{MAJOR}.{MINOR}.{PATCH}-older" if PATCH == 0 else f"{MAJOR}.{MINOR}.{PATCH - 1}", 0),
        ("newer patch: halt", f"{MAJOR}.{MINOR}.{PATCH + 1}", 3),
        ("newer minor: halt", f"{MAJOR}.{MINOR + 1}.0", 3),
        ("newer major: halt", f"{MAJOR + 1}.0.0", 3),
        ("newer with a v and a suffix: halt", f"v{MAJOR}.{MINOR}.{PATCH + 1}-beta", 3),
        ("not a version: ignored, ok", "latest", 0),
        ("no plugin_version (old spec): ok", None, 0),
    ):
        head = {"id": "x", "target": "terraform"}
        if version is not None:
            head["plugin_version"] = version
        code, out = run(head)
        results.append(case(name, code == expected, f"exit {code}: {out}"))
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
