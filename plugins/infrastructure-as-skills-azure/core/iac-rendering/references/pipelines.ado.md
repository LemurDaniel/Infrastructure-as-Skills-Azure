# Pipeline on Azure DevOps

`deployment.deploy_mechanism: azure_devops`. The flow, the invariants and the decision
mapping are in [pipelines.md](pipelines.md); this file is the Azure DevOps spelling of
them, for Terraform and for Bicep.

Status: written from the vendor documentation and a working scaffold of the owner's. It has
been parsed, not run against a project. The `idToken` environment variable of
`AzureCLI@2` and the `lockBehavior` of an environment are the two parts to confirm on the
first run.

## Files

```
azure-pipelines.yml                       # entry: validate, then one stage per environment
.azure-pipelines/stage.yml                # template: plan -> apply for one stage
.azure-pipelines/terraform-install.yml    # Terraform only: the pinned install, once
```

The scaffold repeated the Terraform install script in three jobs; here it is one step
template. The approval is an **environment check**, not the `ManualValidation@1` task the
scaffold used: the task's approver list was broken (the workaround was "anyone with
permission may approve, including the author"), and an environment check holds a real
approver list, a timeout and an optional separation from the author.

## Platform objects

| Object | Per | Holds |
|---|---|---|
| Service connection, type *Azure Resource Manager - workload identity federation* | stage | The stage's identity. Named `sc-<workload>-<stage>` unless the repository has a convention |
| Environment `<stage>` | stage | The approval check on a gated stage (`pipeline_approvals`), and optionally an *Exclusive lock* check |
| Variable group `iac-<workload>-<stage>` | stage | The identifiers below |

Variables of the group - identifiers, none a secret:

| Variable | Target | Value |
|---|---|---|
| `TF_STATE_SUBSCRIPTION_ID`, `TF_STATE_RESOURCE_GROUP`, `TF_STATE_STORAGE_ACCOUNT`, `TF_STATE_CONTAINER` | Terraform | The state backend |
| `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP` | Bicep | The deployment target; Terraform reads both from `environments/<stage>.tfvars` |

Authorize the service connection and the variable group for this pipeline only, not for
all pipelines. With `stage_isolation: subscription` each connection's identity holds the
roles of its own subscription, and `Storage Blob Data Contributor` on the state account.

## Entry pipeline

```yaml
# Rendered from infra-spec.yaml. Platform prerequisites: see pipelines.ado.md.
trigger:
  branches: { include: [master] }
  paths: { include: ["**/*.tf", "**/*.tfvars", "**/*.bicep", "**/*.bicepparam", "azure-pipelines.yml", ".azure-pipelines/**"] }
pr:
  branches: { include: [master] }

pool:
  vmImage: ubuntu-latest

# Terraform only - a Bicep root has no TF_VERSION and renders no `variables:` block here.
variables:
  - name: TF_VERSION
    value: "1.16.6"           # the newest patch of the ~> 1.16.0 constraint on 2026-10-18; re-resolve on render

stages:
  - stage: validate
    displayName: Validate
    jobs:
      - job: validate
        steps:
          - checkout: self
          # the target's validate steps, below

  - template: .azure-pipelines/stage.yml
    parameters:
      stage: development
      dependsOn: validate
      gated: false
      serviceConnection: sc-payments-development

  - template: .azure-pipelines/stage.yml
    parameters:
      stage: test
      dependsOn: development
      gated: false
      serviceConnection: sc-payments-test

  - template: .azure-pipelines/stage.yml
    parameters:
      stage: production
      dependsOn: test
      gated: true             # pipeline_approvals: production - the check lives on the environment
      serviceConnection: sc-payments-production
```

A pull request runs `validate` only: every stage template carries
`condition: ne(variables['Build.Reason'], 'PullRequest')`, so a PR build cannot reach a
service connection.

### Validate steps - Terraform

```yaml
          - template: .azure-pipelines/terraform-install.yml
          - script: terraform fmt -check -recursive
            displayName: Format
          - script: terraform init -backend=false -input=false
            displayName: Init (no backend)
          - script: terraform validate
            displayName: Validate
          - script: terraform test
            displayName: Test
```

### Validate steps - Bicep

```yaml
          - script: az bicep build --file main.bicep --stdout > /dev/null
            displayName: Build
          - script: az bicep lint --file main.bicep
            displayName: Lint
          - script: for f in main.*.bicepparam; do az bicep build-params --file "$f" --stdout > /dev/null; done
            displayName: Parameter files compile against the template
```

## Terraform install - `.azure-pipelines/terraform-install.yml`

```yaml
steps:
  - bash: |
      set -euo pipefail
      v="$(TF_VERSION)"
      cd "$(Agent.TempDirectory)"
      curl -fsSLO "https://releases.hashicorp.com/terraform/${v}/terraform_${v}_linux_amd64.zip"
      curl -fsSLO "https://releases.hashicorp.com/terraform/${v}/terraform_${v}_SHA256SUMS"
      grep "terraform_${v}_linux_amd64.zip" "terraform_${v}_SHA256SUMS" | sha256sum -c -
      mkdir -p "$(Agent.TempDirectory)/tf" && unzip -oq "terraform_${v}_linux_amd64.zip" -d "$(Agent.TempDirectory)/tf"
      echo "##vso[task.prependpath]$(Agent.TempDirectory)/tf"
    displayName: Install Terraform $(TF_VERSION)
```

The checksum guards a corrupt download, not a hostile mirror; an organisation that mirrors
Terraform internally swaps the URL and keeps the shape.

## Stage template - `.azure-pipelines/stage.yml`

```yaml
parameters:
  - name: stage
    type: string
  - name: dependsOn
    type: string
  - name: gated
    type: boolean
  - name: serviceConnection
    type: string

stages:
  - stage: ${{ parameters.stage }}
    displayName: ${{ parameters.stage }}
    dependsOn: ${{ parameters.dependsOn }}
    condition: and(succeeded(), ne(variables['Build.Reason'], 'PullRequest'))
    variables:
      - group: iac-payments-${{ parameters.stage }}
      - name: STAGE
        value: ${{ parameters.stage }}
    jobs:
      - job: plan
        steps:
          - checkout: self
          - bash: |
              f="environments/$(STAGE).tfvars"      # Bicep: main.$(STAGE).bicepparam
              [ -f "$f" ] || { echo "##vso[task.logissue type=error]$f is missing"; exit 1; }
              if grep -Eq '00000000-0000-0000-0000-000000000000|OPEN-|ASSUMED:' "$f"; then
                echo "##vso[task.logissue type=error]Stage $(STAGE) still holds placeholder values in $f - answer the open items first."
                exit 1
              fi
            displayName: Refuse placeholder values
          # Terraform:
          - template: terraform-install.yml
          - task: AzureCLI@2
            displayName: Init and plan
            name: plan
            inputs:
              azureSubscription: ${{ parameters.serviceConnection }}
              addSpnToEnvironment: true
              scriptType: bash
              scriptLocation: inlineScript
              inlineScript: |
                set -uo pipefail
                export ARM_USE_OIDC=true ARM_USE_AZUREAD=true
                export ARM_CLIENT_ID="$servicePrincipalId" ARM_TENANT_ID="$tenantId" ARM_OIDC_TOKEN="$idToken"
                terraform init -input=false \
                  -backend-config="subscription_id=$(TF_STATE_SUBSCRIPTION_ID)" \
                  -backend-config="resource_group_name=$(TF_STATE_RESOURCE_GROUP)" \
                  -backend-config="storage_account_name=$(TF_STATE_STORAGE_ACCOUNT)" \
                  -backend-config="container_name=$(TF_STATE_CONTAINER)" \
                  -backend-config="key=payments/$(STAGE).tfstate" \
                  -backend-config="use_azuread_auth=true" || exit 1
                terraform plan -input=false -detailed-exitcode \
                  -var-file="environments/$(STAGE).tfvars" -out="$(Build.ArtifactStagingDirectory)/tfplan"
                code=$?
                [ "$code" -eq 1 ] && exit 1
                echo "##vso[task.setvariable variable=changes;isOutput=true]$([ "$code" -eq 2 ] && echo true || echo false)"
                terraform show -no-color "$(Build.ArtifactStagingDirectory)/tfplan"
                terraform show -json "$(Build.ArtifactStagingDirectory)/tfplan" | jq -e '[.resource_changes[]? | select(.change.actions | index("delete")) | select(.type == "azurerm_resource_group" or (.type == "azapi_resource" and ((.change.before.type // "") | startswith("Microsoft.Resources/resourceGroups"))))] | length == 0' > /dev/null \n                  || { echo "##vso[task.logissue type=error]The plan deletes a resource group - a group is destroyed by hand, never by the pipeline."; exit 1; }
          - task: PublishPipelineArtifact@1
            condition: eq(variables['plan.changes'], 'true')
            inputs:
              targetPath: $(Build.ArtifactStagingDirectory)/tfplan
              artifact: tfplan-${{ parameters.stage }}

      # A deployment job runs in the environment, so the environment's approval check
      # stops it - and a skipped job never asks. No change, no approval.
      - deployment: apply
        dependsOn: plan
        condition: eq(dependencies.plan.outputs['plan.changes'], 'true')
        environment: ${{ parameters.stage }}
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self
                - template: terraform-install.yml
                # the plan artifact is downloaded to $(Pipeline.Workspace)/tfplan-<stage>/tfplan
                - task: AzureCLI@2
                  displayName: Apply the approved plan
                  inputs:
                    azureSubscription: ${{ parameters.serviceConnection }}
                    addSpnToEnvironment: true
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      set -euo pipefail
                      export ARM_USE_OIDC=true ARM_USE_AZUREAD=true
                      export ARM_CLIENT_ID="$servicePrincipalId" ARM_TENANT_ID="$tenantId" ARM_OIDC_TOKEN="$idToken"
                      terraform init -input=false \
                        -backend-config="subscription_id=$(TF_STATE_SUBSCRIPTION_ID)" \
                        -backend-config="resource_group_name=$(TF_STATE_RESOURCE_GROUP)" \
                        -backend-config="storage_account_name=$(TF_STATE_STORAGE_ACCOUNT)" \
                        -backend-config="container_name=$(TF_STATE_CONTAINER)" \
                        -backend-config="key=payments/$(STAGE).tfstate" \
                        -backend-config="use_azuread_auth=true"
                      terraform apply -input=false "$(Pipeline.Workspace)/tfplan-$(STAGE)/tfplan"
```

Whether the stage is gated is a property of the environment, not of this file: the
`gated` parameter exists so the render and the header comment agree on which environment
needs the approval check, and a reviewer can read it in the entry file.

Queue, never cancel: add an *Exclusive lock* check to the environment, behaviour
*sequential* - two runs wait for each other instead of racing for the state lock.

## Stage template - Bicep

Same parameters and stage skeleton; the jobs below replace the Terraform ones and the
`terraform-install.yml` template is not rendered. A root that is not the repository root
(`bicep/`) puts `workingDirectory: <root>` on every step, `checkout` aside; the paths below
are then relative to it. Variables `AZURE_SUBSCRIPTION_ID` and `AZURE_RESOURCE_GROUP` come from the group.
A root at `deployment_scope: subscription` swaps `az deployment group` for `az deployment sub`
and adds `--location`, in what-if and create alike (invariant 13).

```yaml
      - job: plan
        steps:
          - checkout: self
          - bash: |
              f="main.$(STAGE).bicepparam"
              [ -f "$f" ] || { echo "##vso[task.logissue type=error]$f is missing"; exit 1; }
              if grep -Eq '00000000-0000-0000-0000-000000000000|OPEN-|ASSUMED:' "$f"; then
                echo "##vso[task.logissue type=error]Stage $(STAGE) still holds placeholder values in $f - answer the open items first."
                exit 1
              fi
            displayName: Refuse placeholder values
          - task: AzureCLI@2
            displayName: What-if
            name: plan
            inputs:
              azureSubscription: ${{ parameters.serviceConnection }}
              scriptType: bash
              scriptLocation: inlineScript
              inlineScript: |
                set -euo pipefail
                az deployment group what-if --subscription "$(AZURE_SUBSCRIPTION_ID)" \
                  --resource-group "$(AZURE_RESOURCE_GROUP)" --template-file main.bicep \
                  --parameters "main.$(STAGE).bicepparam" --no-pretty-print > whatif.json
                n=$(jq '[.changes[] | select(.changeType != "NoChange" and .changeType != "Ignore")] | length' whatif.json)
                echo "##vso[task.setvariable variable=changes;isOutput=true]$([ "$n" -gt 0 ] && echo true || echo false)"
                jq -r '.changes[] | select(.changeType != "NoChange" and .changeType != "Ignore") | "\(.changeType)\t\(.resourceId)"' whatif.json

      - deployment: apply
        dependsOn: plan
        condition: eq(dependencies.plan.outputs['plan.changes'], 'true')
        environment: ${{ parameters.stage }}
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self
                # The approver read a prediction: what-if is read-only and create redeploys.
                - task: AzureCLI@2
                  displayName: Deploy
                  inputs:
                    azureSubscription: ${{ parameters.serviceConnection }}
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      az deployment group create --name "payments-$(STAGE)" \
                        --subscription "$(AZURE_SUBSCRIPTION_ID)" --resource-group "$(AZURE_RESOURCE_GROUP)" \
                        --template-file main.bicep --parameters "main.$(STAGE).bicepparam"
```

## Left out of the scaffold

- `ManualValidation@1`, see above.
- `PublishBuildArtifacts@1` / `DownloadPipelineArtifact@2` with a Container location:
  `PublishPipelineArtifact@1` is the current task, and a deployment job downloads the run's
  artifacts on its own.
- The Terraform path in a PowerShell task with a hand-rolled version cache: one bash step
  with a checksum.
- Fixed `dev` / `prod` and an `environment` pipeline parameter: the stages are the spec's,
  chained, and nobody picks one at queue time.
- The "Fallback" block with state and subscription values in comments: they live in the
  variable group or they are an `open:` item.
