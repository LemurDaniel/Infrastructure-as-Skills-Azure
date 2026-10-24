#Requires -Version 7
<#
  Rendered from infra-spec.yaml (chat-sandbox, deployment.deploy_mechanism: local).
  No pipeline: this script runs the same flow a pipeline would - validate, plan, a
  person's confirmation, apply from the saved plan - from a workstation, signed in
  through the current `az login`. Run it from anywhere; it changes into its own
  directory, the Terraform root.

    ./deploy.ps1 -Stage sandbox

  Stages: sandbox (context.environments). One state per stage, chosen by the backend
  key <workload>/<stage>.tfstate -> chat/sandbox.tfstate; never a workspace.

  What a pipeline would give and this script does not: no record of who applied what,
  no separation between the person who plans and the one who applies, and the stage's
  credentials on a laptop. The person at the keyboard is the approval.

  ---- Before the first run (the platform side; this script creates none of it) ----

  1. The state storage account. Passed as parameters or the environment variables
     below; nothing is held here as a literal. Blob versioning and soft delete on the
     container are recommended - the state is the only copy of the mapping.
       TF_STATE_SUBSCRIPTION_ID   subscription of the state account
       TF_STATE_RESOURCE_GROUP    its resource group
       TF_STATE_STORAGE_ACCOUNT   the account
       TF_STATE_CONTAINER         the blob container (e.g. tfstate)
     The backend authenticates with Entra ID (use_azuread_auth=true, ARM_USE_AZUREAD),
     so the account can keep shared keys off.

  2. The identity that runs it: the user of `az login` (same tenant as the target
     subscription). It needs
       - Storage Blob Data Contributor on the state container (or account);
       - Contributor on the target resource group of the stage (environments/
         sandbox.tfvars: subscription_id, resource_group_name) - the resource group
         exists already, this root does not create it;
       - Role Based Access Control Administrator (or User Access Administrator) on that
         resource group: res.role-assignments.tf grants the app's and the search
         service's identities their data-plane roles;
       - Key Vault Secrets Officer on the key vault (RBAC vault): the apply writes the
         placeholder secret of key-vault.security.secret_placeholders (res.key-vault.tf).
         Contributor does not cover the data plane, and this role is not among the
         spec's role assignments.
         On the very first apply the vault does not exist before the secret is written,
         so grant the role at resource-group scope, or expect the first apply to fail
         on the secret and re-run after granting it on the new vault;
       - the Microsoft.CognitiveServices, Microsoft.Search, Microsoft.Web,
         Microsoft.KeyVault, Microsoft.Storage and Microsoft.OperationalInsights
         resource providers registered on the target subscription.

  3. The spec's open: entries. All three block apply, and the stage file holds their
     placeholders (the all-zero GUID, OPEN-...) until they are answered - this script
     refuses a stage file that still holds either marker, before any login or init:
       - resources.app-service.runtime.container_image   (Workload-Team): image, tag
         and registry; and AcrPull for the app's identity on that registry is wiring
         outside this root (output web_app_principal_id);
       - resources.foundry.models.model_deployments       (Workload-Team): model and
         version looked up in the region's catalogue as DataZoneStandard;
       - wiring.entra_app_registration                    (Identity-Team): a directory
         object, not a resource. After the apply, write its client secret into the
         placeholder by hand - never into a file of this repository:
           az keyvault secret set --vault-name <vault> --name <placeholder> --value <secret>
         (the vault from `terraform output key_vault_uri`, the placeholder's name from
         res.key-vault.tf). The next apply keeps the value (lifecycle ignore_changes).
     Not in the spec at all: the stage's subscription_id and resource_group_name are
     placeholders in the same file until the workload owner names them.

  Needs: PowerShell 7, Terraform >= 1.9 (providers.tf) and the Azure CLI on PATH.
  The plan file is written to the system temp directory and removed when the script
  ends, applied or not - it can hold sensitive values in clear.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)] [ValidateSet('sandbox')] [string] $Stage,
  [string] $StateSubscriptionId = $env:TF_STATE_SUBSCRIPTION_ID,
  [string] $StateResourceGroup  = $env:TF_STATE_RESOURCE_GROUP,
  [string] $StateStorageAccount = $env:TF_STATE_STORAGE_ACCOUNT,
  [string] $StateContainer      = $env:TF_STATE_CONTAINER,
  [string] $Workload            = 'chat'
)
$ErrorActionPreference = 'Stop'
$plan = Join-Path ([IO.Path]::GetTempPath()) "tfplan-$Stage-$PID"
$env:ARM_USE_AZUREAD = 'true'

Push-Location $PSScriptRoot
try {
  # A placeholder never deploys: a stage whose open items are unanswered stops here,
  # before any login and before init (pipelines.md, invariant 11).
  $stageFile = "environments/$Stage.tfvars"
  if (-not (Test-Path $stageFile)) { throw "$stageFile is missing" }
  if (Select-String -Path $stageFile -Pattern '00000000-0000-0000-0000-000000000000|OPEN-' -Quiet) {
    throw "Stage $Stage still holds placeholder values in $stageFile - answer the spec's open: entries first (see the header)."
  }

  foreach ($p in 'StateSubscriptionId', 'StateResourceGroup', 'StateStorageAccount', 'StateContainer') {
    if (-not (Get-Variable $p -ValueOnly)) { throw "-$p is empty - pass it or set TF_STATE_* (see the header)" }
  }

  # Validate, without Azure: the same step every pipeline runs before any stage.
  terraform fmt -check -recursive;                 if ($LASTEXITCODE) { throw 'terraform fmt: files need formatting' }
  terraform init -input=false -backend=false;      if ($LASTEXITCODE) { throw 'terraform init (validate) failed' }
  terraform validate;                              if ($LASTEXITCODE) { throw 'terraform validate failed' }
  terraform test;                                  if ($LASTEXITCODE) { throw 'terraform test failed' }

  # The stage's state. -reconfigure: the backend init above saved nothing, and a
  # previous run on this machine must not be migrated into this stage's key.
  terraform init -input=false -reconfigure `
    "-backend-config=subscription_id=$StateSubscriptionId" `
    "-backend-config=resource_group_name=$StateResourceGroup" `
    "-backend-config=storage_account_name=$StateStorageAccount" `
    "-backend-config=container_name=$StateContainer" `
    "-backend-config=key=$Workload/$Stage.tfstate" `
    '-backend-config=use_azuread_auth=true';       if ($LASTEXITCODE) { throw 'terraform init failed' }

  terraform plan -input=false -detailed-exitcode "-var-file=environments/$Stage.tfvars" "-out=$plan"
  switch ($LASTEXITCODE) { 0 { Write-Host 'No changes.'; return } 1 { throw 'terraform plan failed' } }

  # The confirmation is asked only when the plan has changes; the answer approves the
  # saved plan, and the apply below applies exactly that file, never a fresh plan.
  $answer = Read-Host "Apply this plan to '$Stage'? [y/N]"
  if ($answer -ne 'y') { Write-Host 'Not applied.'; return }
  terraform apply -input=false $plan;              if ($LASTEXITCODE) { throw 'terraform apply failed' }
}
finally {
  Remove-Item $plan -ErrorAction SilentlyContinue
  Pop-Location
}
