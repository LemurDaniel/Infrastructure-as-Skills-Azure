#!/usr/bin/env python3
"""Tests write_naming.py: every root gets a full naming.yaml, a deployed Bicep root keeps its names.

    python run_naming_tests.py

A fresh root gets the default as it is; a Bicep root whose Key Vault predates <LOCATION> and
whose storage account predates <UNIQUE_ID_4> gets the copy with their own patterns; an existing
file, a Terraform root on another naming source, a name var it cannot read and an abbreviation
two types share are each left alone.
write_spec.py writes the file too, and its --check writes nothing.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "write_naming.py"
WRITE_SPEC = HERE.parents[1] / "iac-authoring" / "scripts" / "write_spec.py"
DEFAULT = HERE.parent / "references" / "naming.default.yaml"
DEFAULT_TEXT = DEFAULT.read_text(encoding="utf-8")
DEFAULT_KV = yaml.safe_load(DEFAULT_TEXT)["patterns"]["Azure"]["Microsoft.KeyVault/vaults"]["default"]

OLD_KV = "<TYPE>-<ENVIRONMENT>-<NAME>-<UNIQUE_ID_4>"
OLD_ST = "<TYPE><LOCATION><ENVIRONMENT><NAME><INDEX;%02s>"
BICEP = """\
var keyVaultName = 'kv-${env}-${workload}-${uid4}'
var storageAccountName = toLower('st${loc}${env}${workload}${idx}')
var vaultPrivateEndpointName = 'pep-${loc}-${env}-${workload}-vault-${idx}'
"""


def spec(target, **deployment):
    return {"schema_version": 1, "spec": {"id": "t", "target": target},
            "context": {"environments": ["development"], "location": "westeurope", "workload": "t"},
            "deployment": {k: {"value": v, "source": "stated"} for k, v in deployment.items()}}


def run(data, *extra, bicep=None, naming=None, script=SCRIPT):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        path = root / "infra-spec.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        if bicep is not None:
            (root / "modules").mkdir()
            (root / "modules" / "main.bicep").write_text(bicep, encoding="utf-8")
        if naming is not None:
            (root / "naming.yaml").write_text(naming, encoding="utf-8")
        p = subprocess.run([sys.executable, str(script), str(path), *extra], capture_output=True, text=True)
        target = root / "naming.yaml"
        written = target.read_text(encoding="utf-8") if target.exists() else None
    return p.returncode, p.stdout + p.stderr, written


def kv(text):
    return yaml.safe_load(text)["patterns"]["Azure"]["Microsoft.KeyVault/vaults"]["default"]


def st(text):
    return yaml.safe_load(text)["patterns"]["Azure"]["Microsoft.Storage/storageAccounts"]["default"]


def case(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL ") + name + ("" if ok else f"\n{detail}"))
    return ok


def main():
    results = [case("the default's Key Vault pattern carries the location", DEFAULT_KV != OLD_KV, DEFAULT_KV)]

    code, out, text = run(spec("terraform"))
    results.append(case("terraform root: the default, byte for byte", code == 0 and text == DEFAULT_TEXT, out))

    code, out, text = run(spec("bicep"))
    results.append(case("fresh bicep root: the default, byte for byte", code == 0 and text == DEFAULT_TEXT, out))

    code, out, text = run(spec("bicep"), bicep=BICEP)
    results.append(case("deployed bicep root: the old Key Vault pattern pinned", code == 0 and text and kv(text) == OLD_KV, out))
    results.append(case("the pin says why", text and "Pinned: the root names it so" in text, out))
    results.append(case("deployed bicep root: the storage pattern before <UNIQUE_ID_4> pinned",
                        text and st(text) == OLD_ST, out))
    results.append(case("only the two older patterns are pinned", text and text.count("Pinned:") == 2, out))
    results.append(case("still a full copy", text and "abbreviations:" in text and "mappings:" in text
                        and len(text.splitlines()) >= len(DEFAULT_TEXT.splitlines()), out))
    results.append(case("a name with a literal sub-name is reported, not pinned",
                        "vaultPrivateEndpointName not read back" in out, out))

    code, out, text = run(spec("bicep"), bicep=BICEP, naming="# ours\n")
    results.append(case("an existing naming.yaml is left as it is", code == 0 and text == "# ours\n", out))

    code, out, text = run(spec("terraform", naming_source="module"))
    results.append(case("terraform on the naming module: no naming.yaml", code == 0 and text is None, out))

    code, out, text = run(spec("bicep"), bicep="var frontDoorName = 'afd-${env}-${workload}-${idx}'\n")
    results.append(case("an abbreviation two types share is not pinned",
                        code == 0 and text == DEFAULT_TEXT and "not pinned, decide by hand" in out, out))

    code, out, text = run(spec("bicep"), "--check")
    results.append(case("--check: missing is exit 1, nothing written", code == 1 and text is None, out))

    code, out, text = run(spec("bicep"), "--no-stamp", bicep=BICEP, script=WRITE_SPEC)
    results.append(case("write_spec.py writes it with the spec", code == 0 and text and kv(text) == OLD_KV, out))

    code, out, text = run(spec("bicep"), "--check", script=WRITE_SPEC)
    results.append(case("write_spec.py --check writes no naming.yaml", text is None, out))

    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} cases passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
