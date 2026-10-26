#!/usr/bin/env python3
"""Tests write_spec.py: the canonical form changes the layout, never the content or a comment.

    python run_write_spec_tests.py

A spec typed out of order - sections reversed, anchors, a stage map out of stage order, a
comment above a resource and one after a value - is written, then written again; the plugin's
own spec fixtures go through the same round trip.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "write_spec.py"
PLUGIN = SCRIPT.parents[3]
INSTALLED = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
DEPLOYMENT_SET = yaml.safe_load((HERE.parent / "questions" / "deployment.yaml").read_text(encoding="utf-8"))
STORAGE_SET = yaml.safe_load((PLUGIN / "resources" / "storage" / "storage-account" / "questions.yaml").read_text(encoding="utf-8"))

MESSY = """\
# The run's own note on top.
open:
- key: context.resource_group_name
  question: Which resource group does this deploy into?
  blocks: apply
resources:
  storage-account:
    security:
      min_tls_version:
        source: default
        value: TLS1_2
    networking:
      private_endpoint_subnet:
        value: &subnets
          production: snet-pe
          development: snet-pe
        source: forced
        forced_by: deployment.network_ownership
    data_protection:
      blob_soft_delete_days:
        value: 7
        source: overridden
        reason: The customer keeps deleted documents for a week, longer than the requirement derives for this stack.
  # The vault holds the app's secrets.
  key-vault:
    networking:
      private_endpoint_subnet:
        value: *subnets
        source: forced
        forced_by: deployment.network_ownership
deployment:
  local_auth:
    value: disabled
    source: default
  outage_impact:
    value: tolerable
    source: asked           # "Ein Ausfall ist aergerlich"
  deploy_mechanism:
    value: github
    source: stated
context:
  workload: demo
  environments:
  - development
  - production
spec:
  target: terraform
  id: demo
  at: 2026-10-17T09:14:00Z
schema_version: 1
"""

UNPLACEABLE = """\
schema_version: 1
spec:
  id: demo
  target: terraform
open:
- key: context.tags
  question: Which tag set does the organisation apply to every resource it deploys into this
    subscription # a comment no key can carry
  blocks: apply
"""


def run(text, *flags):
    """(exit code, output, file text after the run) for a spec written to a temp file."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "infra-spec.yaml"
        path.write_text(text, encoding="utf-8", newline="\n")
        p = subprocess.run([sys.executable, str(SCRIPT), str(path), *flags], capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr, path.read_text(encoding="utf-8")


def case(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL ") + name + ("" if ok else f"\n{detail}"))
    return ok


def without_stamp(spec):
    spec = json.loads(json.dumps(spec, default=str))
    spec.get("spec", {}).pop("plugin_version", None)
    return spec


def main():
    results = []
    code, out, new = run(MESSY)
    results.append(case("a spec out of order is written", code == 0, f"exit {code}: {out}"))
    lines = new.split("\n")

    code2, out2, again = run(new)
    results.append(case("written twice: the same file", code2 == 0 and again == new, out2))
    code3, out3, untouched = run(MESSY, "--check")
    results.append(case("--check on a file out of order: exit 1, nothing written",
                        code3 == 1 and untouched == MESSY, f"exit {code3}: {out3}"))
    code4, out4, _ = run(new, "--check")
    results.append(case("--check on a written file: exit 0", code4 == 0, f"exit {code4}: {out4}"))

    results.append(case("the content reads back the same (the stamp aside)",
                        without_stamp(yaml.safe_load(new)) == without_stamp(yaml.safe_load(MESSY))))
    results.append(case("spec.plugin_version is the installed plugin's",
                        yaml.safe_load(new)["spec"].get("plugin_version") == INSTALLED, new[:300]))
    _, _, unstamped = run(MESSY, "--no-stamp")
    results.append(case("--no-stamp leaves plugin_version out", "plugin_version" not in yaml.safe_load(unstamped)["spec"]))
    results.append(case("no YAML anchor is left", not re.search(r"[&*]subnets\b|[&*]id\d+", new), new))
    results.append(case("the timestamp stays as it was typed", "  at: 2026-10-17T09:14:00Z" in lines, new[:400]))

    sections = [l.split(":")[0] for l in lines if re.match(r"^[a-z_]+:", l)]
    results.append(case("sections in the fixed order",
                        sections == ["schema_version", "spec", "context", "deployment", "resources", "open"], sections))

    order = [g["id"] for g in DEPLOYMENT_SET["groups"]]
    seen = [l.strip()[6:-4] for l in lines if l.startswith("  # --- ") and l.index("#") == 2]
    dep_groups = [g for g in seen if g in order]
    results.append(case("deployment groups as comments, in the order of deployment.yaml",
                        dep_groups == sorted(dep_groups, key=order.index) and "requirements" in dep_groups, seen))
    req = lines.index("  # --- requirements ---")
    results.append(case("a deployment decision under its group's comment",
                        lines[req + 1].startswith("  outage_impact:"), "\n".join(lines[req:req + 3])))

    sto, kv = lines.index("  storage-account:"), lines.index("  key-vault:")
    results.append(case("resources keep the order they were written in, a blank line between them",
                        sto < kv and lines[kv - 2] == "", "\n".join(lines[kv - 3:kv + 1])))
    storage_groups = [g["id"] for g in STORAGE_SET["groups"]]
    present = [l.strip().rstrip(":") for l in lines[sto:kv] if re.match(r"^    [a-z_]+:$", l)]
    results.append(case("a resource's groups in the order of its question set",
                        present == sorted(present, key=storage_groups.index), present))

    results.append(case("a short decision on one line",
                        "      min_tls_version: {value: TLS1_2, source: default}" in lines, new))
    results.append(case("a stage map in the order of context.environments",
                        "{development: snet-pe, production: snet-pe}" in new, new))
    results.append(case("a decision too long for one line keeps its fields on lines of their own",
                        any(l == "      blob_soft_delete_days:" for l in lines), new))

    results.append(case("the comment on top stays on top", lines[0] == "# The run's own note on top.", lines[:2]))
    kv = lines.index("  key-vault:")
    results.append(case("a comment above a resource stays above it",
                        lines[kv - 1] == "  # The vault holds the app's secrets.", "\n".join(lines[kv - 2:kv + 1])))
    results.append(case("a comment after a value stays on its line",
                        any(l.startswith("  outage_impact:") and l.endswith('# "Ein Ausfall ist aergerlich"')
                            or l == '    source: asked  # "Ein Ausfall ist aergerlich"' for l in lines), new))

    code5, out5, kept = run(UNPLACEABLE)
    results.append(case("a comment no key can carry: exit 2, file untouched",
                        code5 == 2 and kept == UNPLACEABLE, f"exit {code5}: {out5}"))

    for fixture in sorted(PLUGIN.glob("core/*/tests/fixtures/*.yaml")):
        text = fixture.read_text(encoding="utf-8")
        if "schema_version" not in text:
            continue
        c1, o1, once = run(text, "--no-stamp")
        c2, o2, twice = run(once, "--no-stamp")
        same = c1 == 0 and yaml.safe_load(once) == yaml.safe_load(text)
        results.append(case(f"fixture {fixture.parent.parent.parent.name}/{fixture.name}: same content, written twice the same",
                            same and c2 == 0 and once == twice, f"exit {c1}/{c2}: {o1}{o2}"))
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
