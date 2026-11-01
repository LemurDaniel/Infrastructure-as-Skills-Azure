# Pipeline on GitHub Actions

`deployment.deploy_mechanism: github`. The flow, the invariants and the decision mapping are
in [pipelines.md](pipelines.md); this file is the GitHub spelling of them, for Terraform and
for Bicep.

Status: written from the vendor documentation and a working scaffold of the owner's, with the
action versions looked up on 2026-10-18. It has been parsed, not run against a repository.

## Files

```
.github/workflows/
  infra.yaml          # entry: validate, then one call per stage, in order
  infra-stage.yaml    # reusable: plan -> approve -> apply for one stage
```

One reusable workflow instead of one file per stage (the scaffold had three near-identical
ones): a change to the flow is one edit, and a stage is a `with:` block.

## Versions (snapshot 2026-10-18 - look them up again)

```bash
git ls-remote --tags --refs https://github.com/<owner>/<action>.git | sed 's#.*/##' | sort -V | tail -3
```

| Action | Major |
|---|---|
| `actions/checkout` | `v7` |
| `hashicorp/setup-terraform` | `v4` |
| `actions/upload-artifact` / `download-artifact` | `v7` / `v8` (a pair; they must agree on the artifact format) |
| `azure/login` | `v3` |
| Terraform | `~> 1.17.0` |

## Environments

Two per stage, because GitHub evaluates an environment's protection rules for every job that
names it:

| Environment | Holds | Protection |
|---|---|---|
| `<stage>` | The stage's variables; the plan and apply jobs run in it, so it is also the OIDC subject | Deployment branches: the default branch only |
| `<stage>-approval` | Nothing | Required reviewers - only on a gated stage (`pipeline_approvals`) |

The approval job is empty on purpose: it exists to stop the run between plan and apply, after
the approver has had the plan in the job summary, and never holds a credential.

Variables of `<stage>` (plain variables, not secrets - all are identifiers):

| Variable | Target | Value |
|---|---|---|
| `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` | both | The stage's identity |
| `TF_STATE_SUBSCRIPTION_ID`, `TF_STATE_RESOURCE_GROUP`, `TF_STATE_STORAGE_ACCOUNT`, `TF_STATE_CONTAINER` | Terraform | The state backend |
| `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP` | Bicep | The deployment target; Terraform reads both from `environments/<stage>.tfvars` |

The identity (an app registration or a user-assigned managed identity) carries one federated
credential per stage: issuer `https://token.actions.githubusercontent.com`, subject
`repo:<owner>/<repo>:environment:<stage>`. With `stage_isolation: subscription` each stage has
its own identity and the roles of its own subscription.

**Read the subject from the repository, do not assemble it.** A repository (or its organisation)
can switch on immutable subjects, and the token then carries the ids:
`repo:<owner>@<owner id>/<repo>@<repo id>:environment:<stage>`. The name-only subject is then
refused at login. `gh api repos/<owner>/<repo>/actions/oidc/customization/sub` says which form
applies (`use_immutable_subject`, `sub_claim_prefix` is the prefix to use), and
`gh api repos/<owner>/<repo> --jq '{id, owner_id: .owner.id}'` gives the ids. The header comment
of the entry workflow names the form the repository uses; where the render cannot ask, it
writes the name-only form and says to check this.

## Stages that are still open

A stage with `open:` entries in the spec still gets its block in the entry workflow, its
environments and variables in the header comment, and its stage file filled with
placeholders. Its plan job fails at the first step, *Refuse placeholder values*, before any
login - and because each stage waits for the one before, nothing behind it runs either.
Filling the file with real values is the whole change that opens it.

## Entry workflow

```yaml
# Rendered from infra-spec.yaml. Platform prerequisites: see pipelines.github.md.
name: Infrastructure

on:
  pull_request:
    paths: ["**.tf", "**.tfvars", "**.bicep", "**.bicepparam", ".github/workflows/infra*.yaml"]
  push:
    branches: [master]
    paths: ["**.tf", "**.tfvars", "**.bicep", "**.bicepparam", ".github/workflows/infra*.yaml"]
  workflow_dispatch:

permissions:
  contents: read

defaults:
  run:
    shell: pwsh

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      # the target's validate steps, below
      - uses: actions/checkout@v7

  development:
    needs: validate
    if: github.event_name != 'pull_request'
    uses: ./.github/workflows/infra-stage.yaml
    permissions:
      contents: read
      id-token: write
    with:
      stage: development
      gated: false

  test:
    needs: development
    uses: ./.github/workflows/infra-stage.yaml
    permissions: { contents: read, id-token: write }
    with: { stage: test, gated: false }

  production:
    needs: test
    uses: ./.github/workflows/infra-stage.yaml
    permissions: { contents: read, id-token: write }
    with: { stage: production, gated: true }   # pipeline_approvals: production
```

A pull request runs `validate` and nothing else: no job in it holds `id-token: write`, so
code nobody has reviewed cannot ask Azure for anything. A skipped `development` skips the
stages behind it.

### Validate steps - Terraform

```yaml
      - uses: actions/checkout@v7
      - uses: hashicorp/setup-terraform@v4
        with:
          terraform_version: "~> 1.17.0"
      - run: terraform fmt -check -recursive
      - run: terraform init -backend=false -input=false
      - run: terraform validate
      - run: terraform test
```

### Validate steps - Bicep

```yaml
      - uses: actions/checkout@v7
      - run: az bicep build --file main.bicep --stdout > $null
      - run: az bicep lint --file main.bicep
      - name: Parameter files compile against the template
        run: |
          foreach ($f in Get-ChildItem main.*.bicepparam) {
            az bicep build-params --file $f.Name --stdout > $null
            if ($LASTEXITCODE) { exit $LASTEXITCODE }
          }
```

## Stage workflow - Terraform

```yaml
name: Infrastructure stage

on:
  workflow_call:
    inputs:
      stage: { type: string, required: true }
      gated: { type: boolean, required: true }

permissions:
  contents: read

# Queue, never cancel: an apply cut off halfway is how state and reality part.
concurrency:
  group: infra-${{ inputs.stage }}
  cancel-in-progress: false

defaults:
  run:
    shell: pwsh

env:
  STAGE: ${{ inputs.stage }}
  ARM_USE_OIDC: "true"
  ARM_USE_AZUREAD: "true"
  ARM_CLIENT_ID: ${{ vars.AZURE_CLIENT_ID }}
  ARM_TENANT_ID: ${{ vars.AZURE_TENANT_ID }}
  TF_IN_AUTOMATION: "true"
  TF_STATE_KEY_PREFIX: payments        # context.workload

jobs:
  plan:
    runs-on: ubuntu-latest
    environment: ${{ inputs.stage }}
    permissions: { contents: read, id-token: write }
    outputs:
      changes: ${{ steps.plan.outputs.changes }}
    steps:
      - uses: actions/checkout@v7
      - name: Refuse placeholder values
        run: |
          $f = "environments/$env:STAGE.tfvars"
          if (-not (Test-Path $f)) { Write-Output "::error::${f} is missing"; exit 1 }
          if (Select-String -Path $f -Pattern '00000000-0000-0000-0000-000000000000|OPEN-|ASSUMED:' -Quiet) {
            Write-Output "::error file=${f}::Stage $env:STAGE still holds placeholder values - answer the open items first."
            exit 1
          }
      - uses: hashicorp/setup-terraform@v4
        with:
          terraform_version: "~> 1.17.0"
          terraform_wrapper: false      # the wrapper swallows the exit code the plan step reads
      - name: Init
        run: |
          terraform init -input=false `
            -backend-config="subscription_id=${{ vars.TF_STATE_SUBSCRIPTION_ID }}" `
            -backend-config="resource_group_name=${{ vars.TF_STATE_RESOURCE_GROUP }}" `
            -backend-config="storage_account_name=${{ vars.TF_STATE_STORAGE_ACCOUNT }}" `
            -backend-config="container_name=${{ vars.TF_STATE_CONTAINER }}" `
            -backend-config="key=$env:TF_STATE_KEY_PREFIX/$env:STAGE.tfstate" `
            -backend-config="use_azuread_auth=true"
      - name: Plan
        id: plan
        run: |
          terraform plan -input=false -detailed-exitcode `
            -var-file="environments/$env:STAGE.tfvars" -out=tfplan
          $code = $LASTEXITCODE
          if ($code -eq 1) { exit 1 }
          "changes=$(($code -eq 2).ToString().ToLower())" | Add-Content $env:GITHUB_OUTPUT
          "### Plan: $env:STAGE", '```', ((terraform show -no-color tfplan) -join "`n"), '```' | Add-Content $env:GITHUB_STEP_SUMMARY
      - name: Refuse a plan that deletes a resource group
        run: |
          $plan = terraform show -json tfplan | ConvertFrom-Json
          $groups = @($plan.resource_changes | Where-Object {
            $_.change.actions -contains 'delete' -and (
              $_.type -eq 'azurerm_resource_group' -or
              ($_.type -eq 'azapi_resource' -and "$($_.change.before.type)".StartsWith('Microsoft.Resources/resourceGroups')))
          })
          if ($groups) {
            Write-Output "::error::The plan deletes a resource group ($($groups.address -join ', ')) - a group is destroyed by hand, never by the pipeline."
            exit 1
          }
      - uses: actions/upload-artifact@v7
        if: steps.plan.outputs.changes == 'true'
        with:
          name: tfplan-${{ inputs.stage }}
          path: tfplan
          retention-days: 1             # a plan file can hold sensitive values in clear

  approve:
    needs: plan
    if: ${{ inputs.gated && needs.plan.outputs.changes == 'true' }}
    runs-on: ubuntu-latest
    environment: ${{ inputs.stage }}-approval
    steps:
      - run: Write-Output "Approved for ${{ inputs.stage }}."

  apply:
    needs: [plan, approve]
    # approve is skipped on an ungated stage; !failure() lets that pass and still stops on a rejection
    if: ${{ !cancelled() && !failure() && needs.plan.outputs.changes == 'true' }}
    runs-on: ubuntu-latest
    environment: ${{ inputs.stage }}
    permissions: { contents: read, id-token: write }
    steps:
      - uses: actions/checkout@v7
      - uses: hashicorp/setup-terraform@v4
        with:
          terraform_version: "~> 1.17.0"
          terraform_wrapper: false
      - uses: actions/download-artifact@v8
        with:
          name: tfplan-${{ inputs.stage }}
      - name: Init
        run: |
          terraform init -input=false `
            -backend-config="subscription_id=${{ vars.TF_STATE_SUBSCRIPTION_ID }}" `
            -backend-config="resource_group_name=${{ vars.TF_STATE_RESOURCE_GROUP }}" `
            -backend-config="storage_account_name=${{ vars.TF_STATE_STORAGE_ACCOUNT }}" `
            -backend-config="container_name=${{ vars.TF_STATE_CONTAINER }}" `
            -backend-config="key=$env:TF_STATE_KEY_PREFIX/$env:STAGE.tfstate" `
            -backend-config="use_azuread_auth=true"
      - name: Apply the approved plan
        run: terraform apply -input=false tfplan
```

`TF_STATE_KEY_PREFIX` is the literal workload when the spec holds it; when `workload` is
`parameterized`, it is `${{ vars.WORKLOAD }}` and `WORKLOAD` joins the stage's variables.

## Stage workflow - Bicep

Same header, `concurrency`, `approve` job and `apply` condition as above; `plan` and
`apply` differ. A root at `deployment_scope: subscription` swaps `az deployment group` for `az deployment sub`
and adds `--location`, in what-if and create alike (invariant 13).

```yaml
jobs:
  plan:
    runs-on: ubuntu-latest
    environment: ${{ inputs.stage }}
    permissions: { contents: read, id-token: write }
    outputs:
      changes: ${{ steps.whatif.outputs.changes }}
    steps:
      - uses: actions/checkout@v7
      - name: Refuse placeholder values
        run: |
          $f = "main.$env:STAGE.bicepparam"
          if (-not (Test-Path $f)) { Write-Output "::error::${f} is missing"; exit 1 }
          if (Select-String -Path $f -Pattern '00000000-0000-0000-0000-000000000000|OPEN-|ASSUMED:' -Quiet) {
            Write-Output "::error file=${f}::Stage $env:STAGE still holds placeholder values - answer the open items first."
            exit 1
          }
      - uses: azure/login@v3
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - name: What-if
        id: whatif
        env:
          RESOURCE_GROUP: ${{ vars.AZURE_RESOURCE_GROUP }}
        run: |
          az deployment group what-if --resource-group $env:RESOURCE_GROUP `
            --template-file main.bicep --parameters "main.$env:STAGE.bicepparam" `
            --no-pretty-print > whatif.json
          if ($LASTEXITCODE) { exit $LASTEXITCODE }
          $whatif = Get-Content whatif.json -Raw | ConvertFrom-Json
          $changes = @($whatif.changes | Where-Object changeType -notin 'NoChange', 'Ignore')
          "changes=$(($changes.Count -gt 0).ToString().ToLower())" | Add-Content $env:GITHUB_OUTPUT
          $summary = @("### What-if: $env:STAGE", '```') + @($changes | ForEach-Object { "$($_.changeType)`t$($_.resourceId)" }) + '```'
          # A module whose parameters use another module's output cannot be expanded before the
          # deployment: what-if skips it and shows none of its resources.
          $skipped = @($whatif.diagnostics | Where-Object code -eq 'NestedDeploymentShortCircuited' | ForEach-Object { ($_.target -split '/')[-1] })
          if ($skipped) {
            $summary += "**Not predicted (what-if cannot expand these modules, they are deployed anyway):** $($skipped -join ', ')"
          }
          $summary | Tee-Object -FilePath $env:GITHUB_STEP_SUMMARY -Append

  approve:
    # unchanged from the Terraform workflow

  apply:
    needs: [plan, approve]
    if: ${{ !cancelled() && !failure() && needs.plan.outputs.changes == 'true' }}
    runs-on: ubuntu-latest
    environment: ${{ inputs.stage }}
    permissions: { contents: read, id-token: write }
    steps:
      - uses: actions/checkout@v7
      - uses: azure/login@v3
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      # The approver read a prediction: what-if is read-only and create redeploys. Same
      # commit, template and parameter file as the plan job - nothing else is promised.
      - name: Deploy
        env:
          RESOURCE_GROUP: ${{ vars.AZURE_RESOURCE_GROUP }}
        run: |
          az deployment group create --name "payments-$env:STAGE" --resource-group $env:RESOURCE_GROUP `
            --template-file main.bicep --parameters "main.$env:STAGE.bicepparam"
```

The filter assumes the `changes[].changeType` shape of `az deployment group what-if
--no-pretty-print`; check it against one real run before relying on the skip.

**What-if is partial for modules, and the step says so.** A module whose parameters use another
module's output (an identity's principal id, a subnet id) gets a `reference()` in the compiled
template that what-if cannot evaluate; it reports `NestedDeploymentShortCircuited` in
`diagnostics` and lists none of that module's resources. A real run of a seven-module root
listed 20 changes and left out five modules, with nothing in the step to say so. The step
therefore prints the list to the job log as well as the summary and names the skipped modules
under it, so the approver knows what the approval does not cover. Do not rewrite the modules to
`existing` lookups to make what-if see them: the resources do not exist before the first run.

## Deployable root below the repository root

GitHub reads workflows only from `.github/workflows/` at the repository root. When the
deployable root is a directory (`eval-agent/infra/`, one of several roots in a repository), the
workflows still go to the root and carry the directory:

- file names are prefixed with the root (`eval-agent-infra.yaml`, `eval-agent-infra-stage.yaml`)
  and the entry calls the prefixed stage file; the concurrency group is prefixed as well, so two
  roots do not queue behind each other;
- the `paths:` filters of the entry name `<root>/**` and the prefixed workflow files, not the
  repository's `**.tf`;
- `defaults.run.working-directory` is `<root>` in the entry's jobs and the stage workflow. The
  paths of `upload-artifact` and `download-artifact` are workspace-relative, not relative to
  that default: `<root>/whatif.json`, `path: <root>`. `::error file=` annotations name
  `<root>/<file>` too;
- **a job's `defaults.run` replaces the workflow's whole block, shell included.** A job that
  sets only `working-directory: <root>` runs every step in bash, and a `> $null` fails with
  "ambiguous redirect". Every job-level `defaults.run` repeats `shell: pwsh`:

  ```yaml
      defaults:
        run:
          shell: pwsh
          working-directory: <root>
  ```
- **a job without a checkout does not inherit a directory that is not there.** The `approve`
  job checks out nothing, and under a workflow-wide `working-directory: <root>` its first step
  fails with "An error occurred trying to start process '/usr/bin/pwsh' with working directory"
  before it runs. Such a job sets `defaults.run.working-directory: .` - with `shell: pwsh`
  beside it, as above.

`check_pipeline.py` fails on a job that has no `actions/checkout` and inherits such a default,
and on a job-level `defaults.run` without `shell: pwsh`.

## Left out of the scaffold

- `auth_type: ClientSecret` and the JSON-in-a-secret `AZURE_AUTH` - federation only; a
  `client_secret` decision is an `open:` item, not a branch of this file.
- The temporary container-registry IP rules: a case of its own, not a default.
- A `what_if_only` input: the gate is `approve`, not a boolean someone can flip at dispatch.
- `azure/login@v1` and `actions/checkout@v4`: superseded, see the table above.
