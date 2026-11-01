---
name: iac-rendering
description: Renders an infra-spec.yaml as Terraform or Bicep (layout, naming, tests). Also for porting between the two targets and reviewing generated code for idiom.
---

# Rendering a spec

This skill is the second half of the pipeline:

```
question set  ──interview──>  infra-spec.yaml  ──render──>  Terraform / Bicep
              [iac-authoring]                  [here]
```

The split is the point. The interview resolves decisions and writes them in a
backend-neutral vocabulary; this layer is the only one allowed to know that
`public_network_access: disabled` is `public_network_access_enabled = false` in one target
and `properties.publicNetworkAccess: 'Disabled'` in the other. Merge the two and the
vocabulary leaks within a week.

So: **never render without a spec.** If there is none, go to
[iac-authoring](../iac-authoring/SKILL.md) and write one first. Rendering straight from a
conversation produces code nobody can regenerate and a decision record that does not exist.

**Version gate: a spec from a newer plugin is not rendered.** Run
`python <plugin>/core/iac-authoring/scripts/check_plugin_version.py <spec>` first. Exit 3 means
`spec.plugin_version` is newer than the installed plugin: halt - render nothing, write nothing -
and follow the version gate in [iac-authoring](../iac-authoring/SKILL.md#before-anything--find-an-existing-spec):
one AskUserQuestion offering the update, no way on with the older plugin. A render that goes
ahead sets `spec.plugin_version` to the installed version.

**Then the digest, before any reference:**
`python <plugin>/core/iac-rendering/scripts/render_digest.py <spec>`. It prints the spec's
shape, every deployment and resource decision under the key path its test names, with
its value, source and what the resource's `render-map.yaml` maps it to for the target and
implementation - the attribute and the literal the value becomes
([render-map.md](references/render-map.md)) - the AVM modules and naming identifier of
each resource, wiring, `assumed` and `open:` entries, and the
reading list: each reference and each resource's rendering reference with the line
ranges that apply to this spec. Read those ranges (Read with offset and limit), not the
whole files; the rest only for a question the digest leaves open. Exit 1 names a gap - a
resource without a question set, `render-map.yaml` or rendering reference - which goes into the
hand-over. The digest's literal is the one to write; a `gap` is rendered the way it says.

## What the spec hands over

| Spec | What this layer does with it |
|---|---|
| `spec.target` | Picks Terraform or Bicep. Never both from one run |
| `composition` | The module split. One `modules` entry is a directory (Terraform) or a file (Bicep) |
| `context` | Variables/parameters shared by every module, resolved once |
| `resources.<id>` | Decisions → attributes and literals, via the resource's `render-map.yaml` (the digest prints them) and its rendering reference |
| `wiring` | Renders into the root, never into a module — only the caller sees both ends |
| `_target_overrides` | Target-specific escape hatches, each `{ value, reason }`; the reason becomes the comment in the code |

The digest reads the spec for the render; the schema behind it is
[../iac-authoring/references/spec.md](../iac-authoring/references/spec.md). Look a key up
there when the digest does not explain it, never infer the shape from an example spec.

## Order of work

1. **Match the repository before the defaults.** An existing layout, module granularity or
   API version wins over anything in the references here. Generated code that does not look
   like its neighbours gets rewritten by hand, and then the spec is stale.
2. **Resolve the Azure Verified Module for each resource** — [avm.md](references/avm.md).
   AVM is the primary rendering target: a resource with an `Available` module renders as a
   call to it, with every decision written out as an input; a resource without one renders
   authored, and the spec records `implementation: authored` with the reason. The module
   version is looked up live and pinned in the code, never recalled. Skip only when the
   spec's `deployment.module_source` is `authored` or the repository already renders the
   resource authored.
3. **Read the target idiom** — [terraform-idiom](references/terraform-idiom.md) or
   [bicep-idiom](references/bicep-idiom.md), not both — and
   [code-structure.md](references/code-structure.md) for the comments: header, table of
   contents, chapters and sections in every file. A `code-style` skill in the session
   replaces its rules, the repository's own style replaces both; the layout stays the idiom's.
4. **Read the resource's own rendering reference**, `<plugin>/resources/<family>/<resource>/{terraform,bicep}.md`.
   `<plugin>` is two levels above this skill's base directory (shown when it loads,
   `.../core/iac-rendering`); `resources/` sits beside `core/`, not inside it. Read it by that
   absolute path. A reference that cannot be read is said in the hand-over, never replaced
   by a rendering of your own: it holds what the spec cannot. It opens with the decision → module input mapping and the rendered call, and holds
   what the spec cannot: which decisions are fixed at creation, which the module does not
   expose, the shape differences between the two targets. The authored rendering follows
   it, for the fallback case and for reading what the module does inside.
5. **Render names from the right mechanism** — [naming.md](references/naming.md). The
   Terraform provider resolves them; in Bicep they are assembled from vars because the
   naming modules are not shipped. Both read the root's `naming.yaml`, never the plugin's
   default, so a re-render keeps every name the root already has. **A root without one gets
   it first, before any name is rendered**, even for a one-line change:
   `python <plugin>/core/iac-rendering/scripts/write_naming.py <spec>` writes the full copy,
   with each type's pattern as an existing Bicep root names it (`write_spec.py` runs it too).
   Never copy the file by hand; a name it reports as not read back is checked by hand.
6. **Write the secure value explicitly**, even where it matches the provider or API
   default. A default can move between versions and an absent attribute is invisible in
   review.
7. **Render the tests with the code, not after it.** Every decision under `resources:`
   in the spec is asserted by exactly one test, and a decision that cannot be observed in
   a plan is marked as such with its reason. A render without its tests is not finished —
   the tests are what make "the code matches the spec" a check instead of a claim, and
   what makes the next re-render a diff instead of a review. The shape per target is in
   the idiom file; `scripts/check_render_coverage.py` fails on an unasserted decision.
8. **Validate before handing over.** Syntactically valid is not done — `fmt` →
   `validate` → `test` → `plan` / `what-if`, then say which diffs are service-affecting,
   and `scripts/check_code_structure.py <root>` for the comments the render wrote.
   Every check is run, never read: a failure is fixed where its message points, not by
   learning from the script what passes. The commands are at the end of each idiom file. **Then show the names**: run
   `scripts/list_names.py <spec>` and hand over the table - every resource with the name it
   will get, before anything is deployed. A name cannot be changed afterwards, and the
   customer knows whether it fits. It works from the spec alone: no tool or login is
   assumed, and no plan is read. What it cannot know is in
   [naming.md](references/naming.md#names-before-the-deploy).
9. **The diagram is the customer's; a render does not touch it.** They signed off on
   `infra-diagram.drawio.png` before this render started (iac-authoring Phase 5), and the
   code is rendered from the same spec the picture was drawn from, so the picture stays as
   agreed. A render never redraws it. The only thing that changes the picture is a change
   to the spec, and that is not the renderer's to make: a finding whose cause is the spec
   goes back to Phase 5, where the spec is corrected, the diagram redrawn
   ([iac-diagram](../iac-diagram/SKILL.md)) and the customer asked again before the render
   continues.
10. **Render the pipeline the spec chose.** `deployment.deploy_mechanism` names the system
    (`github`, `azure_devops`, `gitlab`, `local`); the stages, the approval gate and the
    login come from the same spec as the code. Read [pipelines.md](references/pipelines.md),
    then that system's file, and hand over the platform prerequisites it lists - a pipeline
    that cannot run until an identity and its environments exist must say so. Run
    `scripts/check_pipeline.py <spec>` before handing over; it fails on a missing stage, a
    gate that does not match `pipeline_approvals`, an apply without a saved plan and a
    secret in the file.
11. **Write or update the repository's `CLAUDE.md`, so the spec does not drift.** The
    rendered code will be edited by people and by Claude long after this run - a SKU
    bumped, a retention changed - and every such edit that is not mirrored into
    `infra-spec.yaml` turns the spec into a record of what was once decided. So the render
    leaves an instruction behind in the repository root. The text is
    [references/claude-md-block.md](references/claude-md-block.md), written by
    `scripts/sync_claude_md.py <repo-root> --root <root> --write`, which touches **only** the
    section between its two markers, never the rest of the file (it is the customer's).
    The section names the spec as the source of truth, the rule that a change to the code is
    a change to the spec first, the order for every change however small, what is
    regenerated from it and the checks that prove the two still agree.

    The begin marker carries `rev=<n>`, raised whenever the text changes. A section with a
    lower rev (none counts as 0) is replaced; the same rev is left; a **higher rev was
    written by a newer plugin and is never overwritten**; say in the hand-over that the
    plugin is out of date and should be updated. A damaged marker pair is left
    alone and named. None of this fails a run: the script reports and exits 0.
    `<root>` is the IaC root relative to the repository root (`infra/`, or `.`). Say in
    the hand-over that the section was written or which rev replaced which.
12. **Complete the repository's `.gitignore`.** State, plans and local secrets must not
    reach the repository, and the render is what creates them. Add only the missing lines
    for the rendered target, never rewrite or remove; a pattern that ignores a file the
    render needs committed is named, not edited. Procedure and entries:
    [gitignore.md](references/gitignore.md).
13. **Run it the way Phase 5 settled.** The working mode - **Subagents** or **Same
    session** - was asked once at the start of `iac-authoring` Phase 5, before the diagram
    loop, and holds for this loop too; ask it here only when this render starts in a run
    that never went through Phase 5 (a carried spec rendered on its own), with the Agent
    tool available and several resource families. Subagents run the code loop - code,
    pipeline and a read-only test agent, with a bounded fix loop - after the diagram loop
    has ended with the customer's yes; never both at once. The protocol, the stop rules and
    what goes into an agent's brief are in [agents.md](references/agents.md). Same session
    does the steps above in order, itself. The answer is a working mode, not a decision: it
    is not written to the spec. A small spec, or a host without the Agent tool, is not
    asked - it is rendered in sequence.

## What a render may write

A render writes infrastructure and nothing else. Whoever renders - the same session or the
code, pipeline or fix agent of [agents.md](references/agents.md) - writes only these files:

| What | Files |
|---|---|
| The code and its tests | Terraform: `*.tf`, `*.tftest.hcl`, `*.tfvars`, `.terraform.lock.hcl`. Bicep: `*.bicep`, `*.bicepparam`, `bicepconfig.json`, `tests/*.armtest.yaml` |
| The spec | `infra-spec.yaml`: `plugin_version` and what the render records (`implementation: authored`) |
| The naming convention | `naming.yaml`, only when the root has none (step 5); an existing one is never changed |
| The pipeline | The files of `deploy_mechanism` (step 10) |
| Scripts | `*.ps1` the pipeline or the deployment calls |
| Repository files | `.gitignore` (step 12), the marked section of `CLAUDE.md` (step 11) |

**Application code is never touched**: no `.js`, `.ts`, `.cs`, `.py`, `package.json`,
`Dockerfile` or app configuration - not when it lies inside the render root, not when a
check fails on it, not when the fix is one line. The application belongs to its owner, and a
render that edits it changes behaviour nobody asked the infrastructure to change. When the
code and the infrastructure disagree (an app setting name, a port, a connection string the
app reads), the render follows the spec and names the mismatch in the hand-over. A review or
test agent keeps the same boundary: a finding in application code is cause `other`, goes
into the hand-over and is never routed to an agent to fix.

## Do not invent attributes

A plausible-looking argument that does not exist is worse than asking. Provider schemas
move, and exact spellings are not something to recall from memory.

- **Terraform** — `terraform providers schema -json` in the target directory (needs
  `terraform init`). Narrow it with `jq`; it is megabytes.
- **Bicep** — compile early: `bicep build --stdout <file>` fails loudly on an unknown
  property. For API versions, prefer the one already used in the repository.

When neither is available, name the attribute you are unsure about instead of guessing. A
named uncertainty is cheap to resolve; a wrong argument found at apply time is not.

**A missing `terraform`, `bicep` or `az` does not stop the render, but it is said, in
`context.language`.** Check once before the first check command (`terraform version`,
`bicep --version`), not by letting the call fail. Rendering goes on; what changes is the
hand-over: the code is marked **unverified** (no `fmt`, `validate`, `test` or `bicep build`
ran, so attributes and tests are unchecked), the attributes in doubt are named, and the
install is offered (`winget install Hashicorp.Terraform`, `winget install Microsoft.Bicep`,
`brew install terraform bicep`). Never write "validated" or "tests pass" for a check that
did not run.

> de: `terraform` ist auf diesem Rechner nicht installiert. Ich rendere trotzdem, aber der
> Code ist **ungeprüft**: weder `fmt` noch `validate` noch `terraform test` sind gelaufen.
> Ungeprüft sind vor allem Argumentnamen und die Tests. Installation:
> `winget install Hashicorp.Terraform`, danach prüfe ich nach.
>
> en: `terraform` is not installed on this machine. I render anyway, but the code is
> **unverified**: `fmt`, `validate` and `terraform test` have not run. Argument names and
> the tests are what is unchecked. Install it with `winget install Hashicorp.Terraform` and
> I check again.

## Porting between the two targets

A spec rendered twice should differ only where the platforms genuinely differ. The
asymmetries that do not survive a naive port are called out in each idiom file — module
scope versus provider aliases, deployment names, where soft delete lives, how replication
is spelled. A port that reads as a transliteration has usually lost one of them.

## Reference files

| File | When |
|---|---|
| [references/avm.md](references/avm.md) | Always, before the idiom: which module, which version, the shared interfaces, the test contract with a module in the middle |
| [references/naming.md](references/naming.md) | Always, before rendering a name |
| [references/terraform-idiom.md](references/terraform-idiom.md) | Target is Terraform |
| [references/bicep-idiom.md](references/bicep-idiom.md) | Target is Bicep |
| [references/code-structure.md](references/code-structure.md) | Always, with the idiom: how every rendered file is commented, and when a `code-style` skill takes over |
| [references/pipelines.md](references/pipelines.md) | Always, after the code: the flow and invariants every pipeline shares |
| [references/pipelines.github.md](references/pipelines.github.md), [.ado.md](references/pipelines.ado.md), [.gitlab.md](references/pipelines.gitlab.md), [.local.md](references/pipelines.local.md) | `deploy_mechanism` is that system |
| [references/gitignore.md](references/gitignore.md) | After rendering: the lines the repository's `.gitignore` must have, added never rewritten |
| [references/agents.md](references/agents.md) | The Agent tool is available and the spec spans several families: the two loops in sequence, the stop rules, the briefs |
| [references/render-map.md](references/render-map.md) | A digest line is unclear, or a resource's `render-map.yaml` is written or changed |
| `scripts/render_digest.py` | First, after the version gate: the spec's decisions with the literal their `render-map.yaml` gives, and the line ranges of every reference this spec needs |
| [../iac-authoring/references/spec.md](../iac-authoring/references/spec.md) | A spec key the digest does not explain |
| [../iac-authoring/references/guardrails.md](../iac-authoring/references/guardrails.md) | A value in the spec looks wrong and you need the rule behind it |
| `scripts/run_arm_tests.py` | A Bicep render: its `tests/*.armtest.yaml` against the compiled ARM |
| `scripts/check_pipeline.py` | After rendering a pipeline: the invariants of `pipelines.md`, per platform |
| `scripts/list_names.py` | After rendering: the names every resource will get, offline from the spec; fails on a length, a character or a duplicate |
| `scripts/check_render_coverage.py` | After rendering, either target: every spec decision asserted or marked, nothing stale |
| `scripts/check_code_structure.py` | After rendering: headers, banner widths, chapters against their steps, tables of contents against the chapters |
