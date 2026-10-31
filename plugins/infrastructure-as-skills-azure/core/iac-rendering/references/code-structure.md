# Code structure

How a rendered file is commented, so it reads top to bottom: a header, a table of contents,
chapters and sections. Comments only - the layout, the file names, the variable and
parameter form and the pipeline shell stay as [terraform-idiom.md](terraform-idiom.md),
[bicep-idiom.md](bicep-idiom.md) and the pipeline files set them, because the tests and
`check_pipeline.py` read them. The rules are the comment part of the
[Storyline code style](https://github.com/LemurDaniel/claude-code-storyline-style)
(storyline-code-style 0.4.0).

## Which rules apply

In this order of precedence:

1. **The repository's own convention.** A root whose files already carry a header or banner
   style keeps it, and the files the render adds follow it (step 1 of the skill).
2. **A `code-style` skill in the session** (the `storyline-code-style` plugin, or the
   person's own). Load it and its reference for the target (`terraform.md`, `bicep.md`,
   `yaml-pipelines.md`) and apply its comment rules: headers, tables of contents, chapters,
   sections, group comments, parameter documentation. Its layout, naming and parameter rules
   do not apply; where it asks for a file the render does not have, the next point says
   where that comment goes instead.
3. **Otherwise the rules below.**

## Banners

Three levels, no fourth: chapter, section, and a one-line group comment inside a unit. The
comment character is the target's - `#` in Terraform, `.tftest.hcl` and YAML, `//` in Bicep.
Every banner line is 75 characters after the comment character and one space.

```hcl
# ===========================================================================
# =========================   DEPLOY THE STORAGE   ==========================
# ===========================================================================
#
#   1. Account            The storage account with every security decision.
#   2. Private endpoint   The endpoint in the workload subnet and its DNS record.
#

# ---------------------------------------------------------------------------
# Account
#   The storage account with every security decision.
# ---------------------------------------------------------------------------

module "storage" {
```

- **Chapter:** three `=` lines, the title in UPPERCASE centered in the middle one with three
  spaces each side, and an activity as title (`DEPLOY THE STORAGE`, never `MAIN`).
  Collection chapters may be `VARIABLES`, `OUTPUTS`, `PARAMETERS`.
- **Chapter description**, framed by an empty comment line above and below: a flow chapter
  numbers its sections (`1. Account   ...`), names exactly as in the section banners, a
  one-line explanation aligned beside each; a collection chapter lists one entry per unit
  without numbers.
- **Section:** two `-` lines, the title in normal case and a one-line description indented
  by three spaces; it repeats the step's explanation. An empty line follows, in YAML the key
  follows directly.
- **Inside a unit** (a module call, a resource, a variable list) no banner: one comment line
  above a group of inputs (`# Network`, `# Data protection`). The `# decision:` and
  `// decision:` comments stay exactly where the idiom puts them; a banner never stands
  between a decision comment and the line it labels.

## Header and table of contents

Every file opens with a header saying what it holds and what must exist first. A file with
chapters lists them below the header, in file order, as its own comment block:

```hcl
# NOTE:
#   Rendered from infra-spec.yaml. Requires: the stage file of the stage planned
#   (environments/<stage>.tfvars) and an authenticated azurerm provider.

#
#   Chapters:
#     DEPLOY THE STORAGE   The account and its private endpoint.
#
```

A tiny file with one unit (a `.bicepparam`, a `.tfvars`, a workflow with one job, an
`.armtest.yaml`) gets the header and no banner.

## Per target

**Terraform.** The root is the book and every `.tf` file one chapter: each opens with its
chapter banner and description - a collection chapter for `variables.tf`, `outputs.tf`,
`locals.tf`, `providers.tf`, a flow chapter with one section per module call or resource
group for an `avm.*.tf` or `res.*.tf`. The table of contents of the root sits in the header
of `providers.tf`, which every root has: every `.tf` file with its chapter title, in reading
order (providers → variables → locals → `avm.*`/`res.*` → outputs). A family module under
`modules/<family>/` is a book of its own, its contents in its `providers.tf` header, or in
`variables.tf` when it has none.

**Terraform tests.** Each `.tftest.hcl` is one chapter whose title names the behaviour
tested (`ASSERT THE SECURITY DECISIONS`); its description lists the `run` blocks by name, one
line each.

**Bicep.** Each file is one book. `main.bicep` reads parameters → names (`var`) → deployment
(the module calls, one section each) → outputs, one chapter per phase; a module under
`modules/` the same, with its resources as sections. `@description` stays the parameter's
documentation; the banner never replaces it.

**Pipelines.** The header is a section-shaped block in the first line: what the pipeline
deploys, the authentication, the variables and environments it needs - the platform
prerequisites the pipeline files already ask for go into it. A workflow with several jobs
has one chapter (`PLAN AND APPLY THE STAGE`) with a section per job, directly above the job
key; a workflow with one job has no banner.

```yaml
jobs:

  # ===========================================================================
  # ======================   PLAN AND APPLY THE STAGE   =======================
  # ===========================================================================
  #
  #   1. Plan      What-if of the stage, uploaded for the approver.
  #   2. Approve   Waits for the stage's approval environment.
  #   3. Apply     Deploys the parameter file the plan resolved.
  #

  # ---------------------------------------------------------------------------
  # Plan
  #   What-if of the stage, uploaded for the approver.
  # ---------------------------------------------------------------------------
  plan:
```

## Before handing over

Run `scripts/check_code_structure.py <root>` on what the render wrote: it counts every
banner line, matches the numbered steps against the sections and each table of contents
against the chapters. A list that names a chapter the file does not have is wrong the same
way a stale test is. Under a `code-style` skill with its own check, run that one as well.
