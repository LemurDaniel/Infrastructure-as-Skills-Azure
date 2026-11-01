#!/usr/bin/env python3
"""Tests check_code_structure.py: a well-commented render passes, each mutation breaks one rule.

    python run_code_structure_tests.py

The render is a Terraform root (providers.tf holding the table of contents, a flow chapter
in avm.storage.tf, a collection chapter in variables.tf), a test file, a Bicep entry point,
its stage file and a workflow with a YAML header. Each mutation changes one line and must
be named by the check: a short banner, a lowercase title, a step without its section, a
section outside a chapter, a missing header, a stale table of contents, a chapter without
description, an unclosed section.
"""

#
#   Chapters:
#     HELPERS                    Banner builders, the run and the case report.
#     THE RENDER                 One well-commented file per kind the render writes.
#     CHECK THE CODE STRUCTURE   The clean render, then one mutation per rule.
#

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "check_code_structure.py"
WIDTH = 75
RULE = "=" * WIDTH


# ===========================================================================
# ===============================   HELPERS   ===============================
# ===========================================================================
#
#   chapter   A chapter banner with its description entries.
#   section   A section banner with title and description.
#   run       Writes the render, applies one mutation, runs the check.
#   case      Prints one result line.
#

def chapter(mark, title, *entries, indent=""):
    core = f"   {title}   "
    left = (WIDTH - len(core)) // 2
    rule = f"{indent}{mark} " + "=" * WIDTH
    lines = [rule, f"{indent}{mark} " + "=" * left + core + "=" * (WIDTH - len(core) - left), rule,
             f"{indent}{mark}"]
    lines += [f"{indent}{mark}   {e}" for e in entries]
    return "\n".join(lines + [f"{indent}{mark}"])


def section(mark, title, description, indent=""):
    rule = f"{indent}{mark} " + "-" * WIDTH
    return "\n".join([rule, f"{indent}{mark} {title}", f"{indent}{mark}   {description}", rule])


def run(mutate=None):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        for rel, text in FILES.items():
            if mutate and mutate[0] == rel:
                assert mutate[1] in text, f"mutation target not in {rel}: {mutate[1]!r}"
                text = text.replace(mutate[1], mutate[2], 1)
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text, encoding="utf-8")
        p = subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def case(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL ") + name + ("" if ok else f"\n{detail}"))
    return ok


# ===========================================================================
# =============================   THE RENDER   ==============================
# ===========================================================================
#
#   PROVIDERS   providers.tf with the root's table of contents.
#   VARIABLES   variables.tf, a collection chapter.
#   STORAGE     avm.storage.tf, a flow chapter with two sections.
#   TEST        A .tftest.hcl with one chapter.
#   BICEP       main.bicep with two chapters.
#   PARAMS      A .bicepparam: the header only.
#   WORKFLOW    A workflow: YAML header, one chapter, a section per job.
#

PROVIDERS =f"""\
# NOTE:
#   Rendered from infra-spec.yaml. Requires: an authenticated azurerm provider.

#
#   Chapters:
#     PROVIDERS            Provider versions and the naming provider.
#     VARIABLES            The context values and the per-stage values.
#     DEPLOY THE STORAGE   The account and its private endpoint.
#

{chapter('#', 'PROVIDERS', 'terraform   The providers this root needs.')}

terraform {{
  required_version = "~> 1.16.0"
}}
"""

VARIABLES = f"""\
# NOTE:
#   The context values of the root and the per-stage values.

{chapter('#', 'VARIABLES', 'location   The region of every resource.')}

variable "location" {{
  description = "(Required) The region, e.g. 'westeurope'."
  type        = string
}}
"""

STORAGE = f"""\
# NOTE:
#   The storage account and its private endpoint.

{chapter('#', 'DEPLOY THE STORAGE', '1. Account            The account with every security decision.', '2. Private endpoint   The endpoint in the workload subnet.')}

{section('#', 'Account', 'The account with every security decision.')}

module "storage" {{
  # decision: storage-account.security.min_tls_version
  min_tls_version = "TLS1_2"
}}

{section('#', 'Private endpoint', 'The endpoint in the workload subnet.')}

resource "terraform_data" "endpoint" {{}}
"""

TEST = f"""\
# NOTE:
#   Plan-only, no credentials.

#
#   Chapters:
#     ASSERT THE SECURITY DECISIONS   One run per question-set group.
#

{chapter('#', 'ASSERT THE SECURITY DECISIONS', 'security   TLS and public access of the account.')}

run "security" {{
  command = plan
}}
"""

BICEP = f"""\
// NOTE:
//   Rendered from infra-spec.yaml. az deployment group create -f main.bicep -p main.production.bicepparam

//
//   Chapters:
//     PARAMETERS             The context values and the stage values.
//     DEPLOY THE WORKLOAD    One module call per family.
//

{chapter('//', 'PARAMETERS', 'location   The region of every resource.')}

param location string

{chapter('//', 'DEPLOY THE WORKLOAD', '1. Storage   The storage family.')}

{section('//', 'Storage', 'The storage family.')}

module storage 'modules/storage.bicep' = {{
  name: 'storage'
}}
"""

PARAMS = """\
// NOTE:
//   The values of stage production.
using 'main.bicep'

param location = 'westeurope'
"""

WORKFLOW = f"""\
{section('#', 'Infrastructure', 'Plans and applies every stage. Azure login through OIDC.')}

#
#   Chapters:
#     PLAN AND APPLY THE STAGE   What-if, approval, deploy.
#

name: Infrastructure

on:
  workflow_dispatch:

jobs:

{chapter('#', 'PLAN AND APPLY THE STAGE', '1. Plan    What-if of the stage.', '2. Apply   Deploys what the plan resolved.', indent='  ')}

{section('#', 'Plan', 'What-if of the stage.', indent='  ')}
  plan:
    runs-on: ubuntu-latest
    steps: []

{section('#', 'Apply', 'Deploys what the plan resolved.', indent='  ')}
  apply:
    needs: plan
    runs-on: ubuntu-latest
    steps: []
"""

FILES = {
    "providers.tf": PROVIDERS,
    "variables.tf": VARIABLES,
    "avm.storage.tf": STORAGE,
    "tests/security.tftest.hcl": TEST,
    "bicep/main.bicep": BICEP,
    "bicep/main.production.bicepparam": PARAMS,
    ".github/workflows/infra.yaml": WORKFLOW,
}


# ===========================================================================
# ======================   CHECK THE CODE STRUCTURE   =======================
# ===========================================================================
#
#   clean render                  The render above passes.
#   short banner line             A rule of 72 characters.
#   lowercase chapter title       `Variables` instead of `VARIABLES`.
#   step without its section      A numbered step whose section is renamed.
#   section outside a chapter     The Bicep chapter banner removed.
#   missing header                The stage file opens with code.
#   stale table of contents       The test file lists another chapter.
#   root without its contents     providers.tf lists nothing.
#   chapter without description   The description block removed.
#   section never closed          The closing `-` line removed.
#   nothing to check              An empty directory exits 2.
#

MUTATIONS = [
    ("short banner line", "avm.storage.tf", "# " + RULE, "# " + RULE[:-3], "characters, not 75"),
    ("lowercase chapter title", "variables.tf", "   VARIABLES   ", "   Variables   ", "is not UPPERCASE"),
    ("step without its section", "avm.storage.tf", "# Private endpoint\n", "# Endpoint\n", "numbers ['Account', 'Private endpoint']"),
    ("section outside a chapter", "bicep/main.bicep", "{chapter}", None, "stands outside a chapter"),
    ("missing header", "bicep/main.production.bicepparam", "// NOTE:\n//   The values of stage production.\n", "", "does not open with a comment"),
    ("stale table of contents", "tests/security.tftest.hcl", "#     ASSERT THE SECURITY DECISIONS", "#     ASSERT THE NETWORK", "table of contents lists"),
    ("root without its table of contents", "providers.tf", "#   Chapters:", "#   Contents:", "lists none"),
    ("chapter without description", "variables.tf", "#\n#   location   The region of every resource.\n#\n", "\n", "has no description"),
    ("section never closed", ".github/workflows/infra.yaml", "  # Apply\n  #   Deploys what the plan resolved.\n  # " + "-" * WIDTH, "  # Apply\n  #   Deploys what the plan resolved.", "never closed"),
]


def main():
    passed = total = 0

    code, out = run()
    total += 1
    passed += case("the well-commented render passes", code == 0, out)

    for name, rel, old, new, expect in MUTATIONS:
        if old == "{chapter}":
            # The Bicep entry point loses the chapter banner above its section.
            text = FILES[rel]
            start = text.index("// " + RULE, text.index("PARAMETERS   ="))
            end = text.index("//\n\n// ---")
            old, new = text[start:end + 3], ""
        code, out = run((rel, old, new))
        total += 1
        passed += case(name, code == 1 and expect in out, out)

    with tempfile.TemporaryDirectory() as d:
        p = subprocess.run([sys.executable, str(SCRIPT), d], capture_output=True, text=True)
    total += 1
    passed += case("nothing to check exits 2", p.returncode == 2, p.stdout)

    print("-" * 70)
    print(f"{passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
