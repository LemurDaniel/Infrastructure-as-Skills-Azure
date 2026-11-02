---
name: iac-unclick
description: Reverse ClickOps (unclick) - reads Azure resources built in the portal, read only, into an infra-spec.yaml that adopts them.
---

# unclick: from what runs to a spec

A second way into the same `infra-spec.yaml`: [iac-authoring](../iac-authoring/SKILL.md) gets
there by interview, this skill by reading what already runs in Azure. From the spec on nothing
is new - the review, the diagram and the render are the existing skills'.

```
Azure (read only) --collect.py--> inventory.json --map_inventory.py--> infra-spec.yaml --> review --> render
```

**Load [iac-authoring](../iac-authoring/SKILL.md) too**: its version gate, its review loop
(Phase 5) and its rules hold here. The spec format is
[spec.md](../iac-authoring/references/spec.md), "Imported resources" for what an import adds.

`<plugin>` is two levels above this skill's base directory; the scripts are in
`<plugin>/core/iac-unclick/scripts/`.

## 1. The scope, asked once

Ask in one AskUserQuestion what is not in the request: the resource group(s) or the
subscription, an optional tag filter, the stage the scope is (`production`, `test`, ...), the
target (Terraform or Bicep). The language is the request's (`de`, `en`), never asked. One
resource group is the reliable case; several groups or a subscription are read, and the
layout of their groups is decided in the review.

## 2. Read - the only step that touches Azure

```
python <plugin>/core/iac-unclick/scripts/collect.py --resource-group <rg> [--tag k=v] --out <dir>/inventory.json
```

Read only: `az graph query`, `az lock list`, `az monitor diagnostic-settings list`. Reader on
the scope is enough. Never run an `az` command that changes anything, and never ask for more
rights than Reader. Without `az` or a login the script says so: tell the person to `az login`
and stop - nothing else in the plugin needs Azure. `--no-diagnostics` skips the one call per
resource on a large scope (then no diagnostic setting is adopted, and the review says so).

## 3. Map - offline

```
python <plugin>/core/iac-unclick/scripts/map_inventory.py <dir>/inventory.json --stage <stage> --target <target> --language <lang> --out <dir>/infra-spec.yaml
python <plugin>/core/iac-authoring/scripts/check_spec.py <dir>/infra-spec.yaml
```

The mapping is data, never judgement: each decision is read through its `import:` entry in the
resource's `render-map.yaml` ([render-map.md](../iac-rendering/references/render-map.md)). Do
not edit the spec to make a value "look right" - the live value is the point. Fix a wrong
reading in the render-map, not in the spec.

## 4. Review - the same loop as an interview's sign-off

Hand over in the person's language, in this order:

1. **What was found**: the resources mapped and their adopted parts, the counts the script
   printed (imported, assumed, unmapped, noise).
2. **Every departure from the guardrails**: each `imported` value that differs from its
   question's `default` - live public access, shared keys, a subnet without NSG. The first
   apply keeps them; hardening one is the person's decision, written as
   `source: { overridden: <reason> }`.
3. **Every `unmapped` item** with its reason, and every `open:` entry - the decisions that
   could not be read are `assumed` and named there.

Then iac-authoring Phase 5: the decision document, the diagram loop, the sign-off. A correction
is a spec change, and the loop runs again.

## 5. Render - not yet

iac-rendering does not write `import` blocks (Terraform) for `adopt` yet. Rendering an imported
spec today would plan to create every resource a second time. **Stop after the sign-off** and
say so: the spec, the decision document and the diagram are the result of this run.

## Rules

- Read only, always. The rest of the plugin never needs a login.
- Nothing drops silently: what has no question set is `unmapped`, what could not be read is
  `assumed` with an `open:` entry.
- Noise (NetworkWatcherRG, managed groups, Smart Detector rules, tags Azure sets) is counted,
  not written.
- The inventory and the spec are the customer's: they belong in their repository, never in
  this plugin.
