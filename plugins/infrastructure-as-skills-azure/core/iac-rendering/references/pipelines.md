# Rendering the pipeline

The pipeline is a render output beside the Terraform or Bicep, drawn from the same spec.
`deployment.deploy_mechanism` picks the file that says how; this file is what every one of
them has in common. Read it first, then exactly one of:

| `deploy_mechanism` | Reference | Files it renders |
|---|---|---|
| `github` | [pipelines.github.md](pipelines.github.md) | `.github/workflows/infra.yaml`, `infra-stage.yaml` |
| `azure_devops` | [pipelines.ado.md](pipelines.ado.md) | `azure-pipelines.yml`, `.azure-pipelines/stage.yml`, `.azure-pipelines/terraform-install.yml` |
| `gitlab` | [pipelines.gitlab.md](pipelines.gitlab.md) | `.gitlab-ci.yml` |
| `local` | [pipelines.local.md](pipelines.local.md) | `deploy.ps1` - no pipeline |

Match the repository first, as everywhere: a repo that already has workflows keeps its
directory, its runner labels and its naming, and the render adds beside them. Never two
pipelines that apply the same state.

## The flow, the same on every platform

```
validate  ──>  [ stage: plan ──> approve? ──> apply ]  ──>  next stage  ──>  ...
 (no Azure)      development                                  test             production
```

One block per entry of `context.environments`, in that order, each waiting for the one
before. A `[sandbox]` spec has one block. The block is the unit:

| Step | Terraform | Bicep |
|---|---|---|
| validate (once, before any stage) | `fmt -check -recursive`, `init -backend=false`, `validate`, `test` | `bicep build`, `bicep lint` |
| plan | `plan -detailed-exitcode -var-file=environments/<stage>.tfvars -out=tfplan` | `az deployment group what-if` with `main.<stage>.bicepparam` |
| changes? | exit code 2 | any change type other than `NoChange` / `Ignore` |
| approve | only if the stage is gated and there are changes | same |
| apply | `apply tfplan` - the file the plan step wrote | `az deployment group create`, same template and parameter file |

## Invariants

These hold on every platform. They are what a review of a rendered pipeline checks, and
what `scripts/check_pipeline.py` asserts - the way `check_render_coverage.py` asserts the
decisions of a render. The check reads what the files can show; the parts that are the
platform's (an environment's approval check, a lock check, the federated credential) it
reports as "not checkable" instead of passing them.

1. **Validate holds no Azure credential.** It runs on every pull request and must be safe
   for code nobody has reviewed yet. Plan and apply run only from the default branch (or a
   manual run of it), never from a pull request.
2. **Apply applies what was approved.** Terraform applies the saved `tfplan` of the same
   run - never a fresh plan, which may differ from the one the approver read. Bicep has no
   saved plan: `what-if` is read-only and `create` redeploys, so the template, parameter
   file and commit are the same run's, and the pipeline says in a comment that the
   approver read a prediction. The prediction can be partial: a Bicep module that takes
   another module's output is skipped by what-if (`NestedDeploymentShortCircuited`), so the
   plan step prints the list to the log and names the skipped modules under it - an approval
   must not look like it covers resources it never showed.
3. **The gate is the platform's, and only on a stage that has changes.** A stage with no
   change skips both approval and apply, so nobody approves an empty plan.
   `pipeline_approvals` says which stages are gated; the rendered job names the
   environment that carries the approval and the header comment lists the check to set on it.
4. **One apply per stage at a time.** Two runs applying one state race for its lock and one
   fails halfway. Every platform has the construct: `concurrency`, an environment lock,
   `resource_group`. It queues, never cancels - cancelling an apply mid-way is how state
   and reality part.
5. **One identity per stage, federated.** `pipeline_auth: workload_identity` means the run
   presents a token and no secret exists. The stage's identity holds the roles of that
   stage's subscription and nothing else. The render names the identity it expects and
   the federated-credential subject; creating them is the platform's, once.
6. **No secret in a file.** Subscription, tenant and client ids, the state account and the
   service connection name are identifiers and are committed or configured as plain
   variables; a client secret (`pipeline_auth: client_secret`) is a platform secret
   reference and an `open:` item for its rotation.
7. **The token is the narrowest the job needs.** GitHub: `permissions: contents: read` at
   the top, `id-token: write` on the Azure jobs only. The other platforms' equivalents
   are named in their files.
8. **A plan file is a secret.** It can hold sensitive values in clear. The artifact keeps
   for one day, and is downloaded by the apply job of the same run only.
9. **Versions are pinned and looked up, never recalled.** The Terraform version as a
   constraint on the minor (`~> 1.16.0`), actions and tasks at a major tag, resolved at
   render time and dated in a comment. The numbers in the platform files are a snapshot of
   2026-10-18 - `git ls-remote --tags --refs <repo>` is how to read the live ones. An
   organisation that requires full-commit pins states it once and the render writes the SHA
   with the tag as a comment.
10. **State comes from the stage, never a workspace.** The backend key is
    `<workload>/<stage>.tfstate` as `terraform-idiom.md` fixes it. The backend account
    (resource group, account, container, and subscription when it is not the stage's) is
    configuration of the stage's environment, passed with `-backend-config`. The code holds
    the empty block `backend "azurerm" {}`: without it `init` ignores every `-backend-config`
    and the state is local.

11. **A placeholder never deploys.** The first step of a stage's plan job - before any login
    and before `init` - fails when the stage's file (`environments/<stage>.tfvars`,
    `main.<stage>.bicepparam`) holds the all-zero GUID, an `OPEN-` value or an `ASSUMED:`
    marker, and says which file and to ask for the spec's `open:` entries and `assumed`
    values. The stage chain then holds every stage
    behind it: nothing rolls out while a stage in front of it is open, which is what the
    decision document tells the customer ("Solange diese Punkte offen sind, wird nichts
    ausgerollt"). The check is the same one line on every platform:
    `grep -Eq '00000000-0000-0000-0000-000000000000|OPEN-|ASSUMED:'`. A resolved stage whose file
    still holds a marker fails it too, which is the point - and the grep reads comments as
    well, so a resolved stage's file must not spell either marker out, not even to explain
    the convention (a staging file once did, and would have refused itself).
12. **A plan that deletes a resource group does not reach apply.** Terraform only: after the
    plan, a step reads `terraform show -json <plan>` and fails when a `delete` hits a
    resource group (`azurerm_resource_group`, or an `azapi_resource` whose type is
    `Microsoft.Resources/resourceGroups`), before the plan is saved as an artifact or sent for
    approval. A group is the unit that takes everything in it along, and an approval that
    scrolls past one line in a long plan is not a safeguard; a deliberate teardown is done by
    hand, outside the pipeline, after the production lock is removed on purpose. Bicep
    deploys incrementally and never deletes: dropping a group from the spec leaves it
    behind, orphaned, and the hand-over says so. The step needs `jq` (or PowerShell in the
    local script); verify the `azapi_resource` branch against the AVM resource group
    module's plan before relying on it.

13. **The deployment command matches `deployment_scope`.** Bicep only: `resource_group` deploys
    with `az deployment group` into the stage's group (the main group, or the first group of a
    split), `subscription` with `az deployment sub` and `--location`, the root at
    `targetScope = 'subscription'` creating its groups. Both what-if and create use the same
    command; a root at one scope deployed with the other fails at the first run.

## What the render hands over besides the files

The pipeline cannot run until the platform side exists, so the render states it, in the
header comment of the entry file and in the reply, as a short list:

- the identity per stage, and the federated-credential subject it must trust;
- the roles that identity needs (under `stage_isolation: resource_group` each assigned on that
  stage's groups only - one on the shared subscription reaches every stage): `Contributor` on the stage's resource groups, every entry
  of `deployment.deployer_roles` with its scope and the decisions it is for (`Role Based
  Access Control Administrator` with a condition limiting it to the roles the spec assigns),
  and `Storage Blob Data Contributor` on the state account;
- under `resource_group_scheme: protection`, that administrator rights on the protected group are
  granted on that group alone ([resource-groups.md](resource-groups.md#roles));
- the platform objects: GitHub environments, an Azure DevOps service connection and
  environments, GitLab protected environments and CI/CD variables;
- the approval check on each gated stage's environment;
- every variable the pipeline reads and where it is set.

Paths in a pipeline are relative to the deployable root. When the root is the repository
root that is `.`; when it is a directory (`bicep/` beside a Terraform root, a `infra/`
folder) the render sets the working directory of every step to it, in the platform's own
construct, and says so in the header comment. A job that checks out nothing (the empty
approval job) does not have that directory on its runner: it resets the working directory
instead of inheriting it. On GitHub the workflows also stay at the repository root whatever
the deployable root is - see [pipelines.github.md](pipelines.github.md#deployable-root-below-the-repository-root).

A stage whose values are `open:` in the spec still gets its block, its variables set and
its stage file, filled with placeholders ([terraform-idiom.md](terraform-idiom.md#the-context-values-and-the-stage-files)):
the scaffold stands, and answering the open items is an edit of values. The header comment
names the stages that still hold placeholders. They cannot deploy - see invariant 11.

## From the decisions

| Decision | Rendered as |
|---|---|
| `context.environments` | The stage blocks, in order |
| `context.workload`, `context.location` | The state key; a `parameterized` value the stage file does not carry is passed as `-var` / a parameter, never a literal |
| `deployment.deploy_mechanism` | Which reference and which files |
| `deployment.pipeline_auth` | The login mechanics of the platform file |
| `deployment.pipeline_approvals` | Which stages have the gate: `production` - the last stage named `production`, or the last stage if none is; `every_stage`; `none` |
| `deployment.deployment_scope` | Bicep: `az deployment group` (`resource_group`) or `az deployment sub` with `--location` (`subscription`), invariant 13. Both targets: the stage identity's Contributor on its groups, or on the subscription |
| `deployment.resource_group_layout` | Bicep: the group the stage deploys into (`AZURE_RESOURCE_GROUP`, `-ResourceGroup`) is the main group, or under `split` the first group of the split, in the scheme's order - the root's modules reach the others by `scope:`. Terraform: nothing |
| `deployment.stage_isolation` | `subscription`: one identity and one subscription per stage. `resource_group`: one subscription, so the identities differ by the role scope on the resource group - every role of a stage's identity is assigned on that stage's groups, never on the subscription, and the hand-over says that a subscription assignment removes the separation |
| `deployment.deployer_roles` | The roles beyond `Contributor` in the hand-over list; nothing in a pipeline step |
| `deployment.non_production_savings` | Nothing in the pipeline; the stage file carries it |
| `target` | Terraform or Bicep column of the flow above |

## Testing a pipeline

A pipeline cannot be planned. Before handing over, run what runs without the platform:

```powershell
# The invariants above, against the files beside the spec (or --root <dir>).
python3 <plugin>/core/iac-rendering/scripts/check_pipeline.py ./infra-spec.yaml

# Syntax and schema of the file, where a tool exists
actionlint .github/workflows/*.yaml                       # GitHub
# Azure DevOps: the Pipelines UI "Validate" or az pipelines (needs the project)
# GitLab: the project's CI Lint (needs the project)

# The files parse, and name every stage of the spec
python3 <plugin>/core/iac-rendering/scripts/check_yaml_parse.py <files>
```

and say what was not run. A pipeline that has only been read has not been tested - the
platform files mark the parts that follow the vendor's documentation without having run
against a real project.

## Not covered

- Creating the identity, the federated credential, the state account or the platform
  objects. The render lists them; a platform team creates them.
- Pull-request plan comments, drift detection on a schedule, and policy scanners. All are
  additions to the flow above, not changes to it, and none is rendered unless the user asks.
- Multi-root repositories: one pipeline per deployable root, in that root's directory, or
  one pipeline with the root as a parameter - match what the repository does.
