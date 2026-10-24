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
