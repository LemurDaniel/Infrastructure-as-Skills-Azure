# Deploying without a pipeline

`deployment.deploy_mechanism: local`. There is no pipeline and no platform object. The
render ships one script, `deploy.ps1`, that runs the same flow as the other platforms -
validate, plan, a person's confirmation, apply - from a workstation. The flow and the
invariants that survive are in [pipelines.md](pipelines.md).

`pipeline_auth` and `pipeline_approvals` are not asked: the person at the keyboard is
signed in with `az login` and is the approval. What is lost against a pipeline is said in
the reply, not hidden: no record of who applied what, no separation between the person who
plans and the one who applies, and a stage's credentials on a laptop.

## What survives of the invariants

| Invariant | Local |
|---|---|
| Apply applies what was approved | Terraform: the saved `tfplan` of the same script run, never a fresh plan. Bicep: what-if, then `create` of the same files |
| Approval only when there are changes | The script asks only when the plan has changes |
| One state per stage | The backend key `<workload>/<stage>.tfstate`, chosen by the script from `-Stage` |
| A plan file is a secret | Written to the system temp directory, deleted after the apply or on exit |
| Production is deliberate | The last stage asks for its name to be typed, not just `y` |

The script takes the state backend and, for Bicep, the target from parameters that default
to environment variables; it holds none of them as literals.

## `deploy.ps1` - Terraform

```powershell
#Requires -Version 7
<#
  Rendered from infra-spec.yaml. Signs in through the current `az login`.
  ./deploy.ps1 -Stage development
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)] [ValidateSet('development', 'test', 'production')] [string] $Stage,
  [string] $StateSubscriptionId = $env:TF_STATE_SUBSCRIPTION_ID,
  [string] $StateResourceGroup  = $env:TF_STATE_RESOURCE_GROUP,
  [string] $StateStorageAccount = $env:TF_STATE_STORAGE_ACCOUNT,
  [string] $StateContainer      = $env:TF_STATE_CONTAINER,
  [string] $Workload            = 'payments'
)
$ErrorActionPreference = 'Stop'
$plan = Join-Path ([IO.Path]::GetTempPath()) "tfplan-$Stage-$PID"
$env:ARM_USE_AZUREAD = 'true'

# A placeholder never deploys: a stage whose open items are unanswered stops here.
$stageFile = "environments/$Stage.tfvars"
if (-not (Test-Path $stageFile)) { throw "$stageFile is missing" }
if (Select-String -Path $stageFile -Pattern '00000000-0000-0000-0000-000000000000|OPEN-' -Quiet) {
  throw "Stage $Stage still holds placeholder values in $stageFile - answer the open items first."
}

try {
  terraform fmt -check -recursive;                 if ($LASTEXITCODE) { throw 'terraform fmt: files need formatting' }
  terraform init -input=false `
    "-backend-config=subscription_id=$StateSubscriptionId" `
    "-backend-config=resource_group_name=$StateResourceGroup" `
    "-backend-config=storage_account_name=$StateStorageAccount" `
    "-backend-config=container_name=$StateContainer" `
    "-backend-config=key=$Workload/$Stage.tfstate" `
    '-backend-config=use_azuread_auth=true';       if ($LASTEXITCODE) { throw 'terraform init failed' }
  terraform validate;                              if ($LASTEXITCODE) { throw 'terraform validate failed' }

  terraform plan -input=false -detailed-exitcode "-var-file=environments/$Stage.tfvars" "-out=$plan"
  switch ($LASTEXITCODE) { 0 { Write-Host 'No changes.'; return } 1 { throw 'terraform plan failed' } }

  $doomed = terraform show -json $plan | ConvertFrom-Json | ForEach-Object { $_.resource_changes } |
    Where-Object { $_.change.actions -contains 'delete' -and ($_.type -eq 'azurerm_resource_group' -or
      ($_.type -eq 'azapi_resource' -and "$($_.change.before.type)" -like 'Microsoft.Resources/resourceGroups*')) }
  if ($doomed) { throw 'The plan deletes a resource group - a group is destroyed by hand, never by the pipeline.' }

  $answer = Read-Host "Apply this plan to '$Stage'? Type the stage name to confirm"
  if ($answer -ne $Stage) { Write-Host 'Not applied.'; return }
  terraform apply -input=false $plan;              if ($LASTEXITCODE) { throw 'terraform apply failed' }
}
finally { Remove-Item $plan -ErrorAction SilentlyContinue }
```

## `deploy.ps1` - Bicep

A root at `deployment_scope: subscription` swaps `az deployment group` for `az deployment sub`
and adds `--location`, in what-if and create alike (invariant 13).

```powershell
#Requires -Version 7
[CmdletBinding()]
param(
  [Parameter(Mandatory)] [ValidateSet('development', 'test', 'production')] [string] $Stage,
  [string] $SubscriptionId = $env:AZURE_SUBSCRIPTION_ID,
  [string] $ResourceGroup  = $env:AZURE_RESOURCE_GROUP,
  [string] $Workload       = 'payments'
)
$ErrorActionPreference = 'Stop'
$params = "main.$Stage.bicepparam"

# A placeholder never deploys: a stage whose open items are unanswered stops here.
if (-not (Test-Path $params)) { throw "$params is missing" }
if (Select-String -Path $params -Pattern '00000000-0000-0000-0000-000000000000|OPEN-' -Quiet) {
  throw "Stage $Stage still holds placeholder values in $params - answer the open items first."
}

az bicep lint --file main.bicep;                   if ($LASTEXITCODE) { throw 'bicep lint failed' }
$whatIf = az deployment group what-if --subscription $SubscriptionId --resource-group $ResourceGroup `
  --template-file main.bicep --parameters $params --no-pretty-print | ConvertFrom-Json
if ($LASTEXITCODE) { throw 'what-if failed' }

$changes = $whatIf.changes | Where-Object { $_.changeType -notin 'NoChange', 'Ignore' }
if (-not $changes) { Write-Host 'No changes.'; return }
$changes | Format-Table changeType, resourceId

# what-if is read-only and create redeploys: the answer approves a prediction.
$answer = Read-Host "Deploy to '$Stage'? Type the stage name to confirm"
if ($answer -ne $Stage) { Write-Host 'Not deployed.'; return }
az deployment group create --name "$Workload-$Stage" --subscription $SubscriptionId `
  --resource-group $ResourceGroup --template-file main.bicep --parameters $params
if ($LASTEXITCODE) { throw 'deployment failed' }
```

The stage list in `ValidateSet` is `context.environments`. A `[sandbox]` spec has one entry
and the confirmation is a plain `y`.
