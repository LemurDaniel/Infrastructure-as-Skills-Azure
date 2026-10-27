#!/usr/bin/env python3
"""Tests list_names.py: the names a small spec gets, and the rules that fail the run.

    python run_names_tests.py
"""
import copy
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "list_names.py"

SPEC = {
    "context": {
        "language": "en", "environments": ["development", "production"], "location": "westeurope",
        "workload": "shop", "resource_group_name": {"development": "rg-x-dev", "production": "rg-x-prod"},
    },
    "deployment": {},
    "resources": {
        "storage-account__host": {}, "storage-account__uploads": {}, "key-vault": {},
        "virtual-network": {"addressing": {"subnets": {"value": {"production": [{"name": "snet-a"}]}}}},
    },
}


def run(spec, *extra, naming=None):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "infra-spec.yaml"
        path.write_text(yaml.safe_dump(spec), encoding="utf-8")
        if naming:
            (Path(d) / "naming.yaml").write_text(yaml.safe_dump(naming), encoding="utf-8")
        p = subprocess.run([sys.executable, str(SCRIPT), str(path), *extra], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def case(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL ") + name + ("" if ok else f"\n{detail}"))
    return ok


def main():
    results = []

    code, out = run(SPEC, "--stage", "production")
    results.append(case("valid spec exits 0", code == 0, out))
    for expected in ("`stweprodshophost01`", "`stweprodshopuploads01`", "`kv-we-prod-shop-????`",
                     "`vnet-we-prod-shop-01`", "`snet-a`", "`rg-x-prod`"):
        results.append(case(f"names {expected}", expected in out, out))
    results.append(case("global name is never reported free", "availability unchecked" in out, out))

    code, out = run(SPEC)
    results.append(case("every stage listed by default", "Stage: development" in out and "Stage: production" in out, out))
    results.append(case("stage code follows the stage", "stwedevshop" in out, out))

    spec = copy.deepcopy(SPEC)
    spec["context"]["workload"] = "paymentsplatformeurope"
    code, out = run(spec, "--stage", "production")
    results.append(case("storage name over 24 chars fails", code == 1 and "allowed 3-24" in out, out))

    spec = copy.deepcopy(SPEC)
    spec["resources"] = {"storage-account": {}, "storage-account__": {}}
    code, out = run(spec, "--stage", "production")
    results.append(case("same name twice fails", code == 1 and "same name as" in out, out))

    code, out = run(SPEC, "--stage", "production", naming={"mappings": {"location": {"westeurope": "weu"}}})
    results.append(case("naming.yaml beside the spec is merged over the default", "stweprodshop" not in out
                        and "stweuprodshophost01" in out.replace("`", ""), out))

    spec = copy.deepcopy(SPEC)
    spec["context"]["location"] = "mars"
    code, out = run(spec)
    results.append(case("location outside the convention is a blocker", code != 0 and "mappings.location" in out, out))

    code, out = run(SPEC, "--stage", "production", "--language", "de")
    results.append(case("--language de", "Aktion" in out, out))

    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} cases passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
