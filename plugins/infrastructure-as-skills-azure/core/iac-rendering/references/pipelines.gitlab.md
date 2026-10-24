# Pipeline on GitLab CI

`deployment.deploy_mechanism: gitlab`. The flow, the invariants and the decision mapping are
in [pipelines.md](pipelines.md); this file is the GitLab spelling of them, for Terraform
and for Bicep.

Status: **untested, and without a scaffold behind it.** The owner's archive has pipelines for
GitHub and Azure DevOps and none for GitLab; this file is written from GitLab's and
Microsoft's documentation alone. Say so in the reply when rendering it, and ask for a first
run on a throwaway project before it reaches production.

## What differs from the other platforms

- **The OIDC subject does not name the stage.** GitLab's token carries `project_path`,
  `ref_type` and `ref` in the subject, not the environment. A federated credential
  therefore trusts "this project, this branch", and every stage's identity can trust the
  same subject. The separation between stages is then the **environment-scoped CI/CD
  variable** that holds the stage's client id - a job in the `production` environment gets
  the production identity and a job in `development` cannot, but only while the variables
  are scoped and the environments protected. State that in the reply: it is weaker than
  the GitHub and Azure DevOps subject, and a reviewer should know.
- **No job-level skip on "no changes".** A job's `rules` cannot read an artifact, so the
  apply job exists on every run. It exits at once with "no changes" when the plan found
  none, but a gated stage still shows the manual button. Dynamic child pipelines would
  remove it and cost a generated file; not rendered unless asked.
- **The gate is `when: manual` on a protected environment.** Approval rules on a deployment
  are a Premium feature; `when: manual` with `allow_failure: false` and protected-environment
  *allowed to deploy* users works on every tier and is what the file renders.

## Platform objects

| Object | Per | Holds |
|---|---|---|
| Environment `<stage>` | stage | Protected; *allowed to deploy*: the approvers (and, on Premium, an approval rule), default branch only |
| CI/CD variables scoped to environment `<stage>` | stage | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and per target the state or deployment identifiers |
| Federated credential | identity | Issuer `https://gitlab.com` (or the instance URL), subject `project_path:<group>/<project>:ref_type:branch:ref:master`, audience `api://AzureADTokenExchange` |

Variables scoped per environment: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`; Terraform adds
`TF_STATE_SUBSCRIPTION_ID`, `TF_STATE_RESOURCE_GROUP`, `TF_STATE_STORAGE_ACCOUNT`,
`TF_STATE_CONTAINER`; Bicep adds `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`. All are
identifiers; none is masked-secret material.

## Terraform - `.gitlab-ci.yml`

```yaml
# Rendered from infra-spec.yaml. Platform prerequisites: see pipelines.gitlab.md.
stages:
  - validate
  - development
  - test
  - production

default:
  image:
    name: hashicorp/terraform:1.16        # latest 1.16.x; re-resolve on render
    entrypoint: [""]

variables:
  TF_IN_AUTOMATION: "true"
  TF_INPUT: "false"
  ARM_USE_OIDC: "true"
  ARM_USE_AZUREAD: "true"
  STATE_KEY_PREFIX: payments              # context.workload

validate:
  stage: validate
  script:
    - terraform fmt -check -recursive
    - terraform init -backend=false
    - terraform validate
    - terraform test

.plan:
  id_tokens:
    AZURE_OIDC_TOKEN:
      aud: api://AzureADTokenExchange
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  script:
    - |
      f="environments/$CI_ENVIRONMENT_NAME.tfvars"      # Bicep: main.$CI_ENVIRONMENT_NAME.bicepparam
      [ -f "$f" ] || { echo "$f is missing"; exit 1; }
      if grep -Eq '00000000-0000-0000-0000-000000000000|OPEN-' "$f"; then
        echo "Stage $CI_ENVIRONMENT_NAME still holds placeholder values in $f - answer the open items first."
        exit 1
      fi
    - export ARM_CLIENT_ID="$AZURE_CLIENT_ID" ARM_TENANT_ID="$AZURE_TENANT_ID" ARM_OIDC_TOKEN="$AZURE_OIDC_TOKEN"
    - >
      terraform init
      -backend-config="subscription_id=$TF_STATE_SUBSCRIPTION_ID"
      -backend-config="resource_group_name=$TF_STATE_RESOURCE_GROUP"
      -backend-config="storage_account_name=$TF_STATE_STORAGE_ACCOUNT"
      -backend-config="container_name=$TF_STATE_CONTAINER"
      -backend-config="key=$STATE_KEY_PREFIX/$CI_ENVIRONMENT_NAME.tfstate"
      -backend-config="use_azuread_auth=true"
    - set +e; terraform plan -detailed-exitcode -var-file="environments/$CI_ENVIRONMENT_NAME.tfvars" -out=tfplan; code=$?; set -e
    - if [ "$code" -eq 1 ]; then exit 1; fi
    - echo "$code" > plan.exitcode
    - terraform show -no-color tfplan
    - terraform show -json tfplan | jq -e '[.resource_changes[]? | select(.change.actions | index("delete")) | select(.type == "azurerm_resource_group" or (.type == "azapi_resource" and ((.change.before.type // "") | startswith("Microsoft.Resources/resourceGroups"))))] | length == 0' > /dev/null || { echo "The plan deletes a resource group - a group is destroyed by hand, never by the pipeline."; exit 1; }
  artifacts:
    paths: [tfplan, plan.exitcode]
    expire_in: 1 day                      # a plan file can hold sensitive values in clear

.apply:
  id_tokens:
    AZURE_OIDC_TOKEN:
      aud: api://AzureADTokenExchange
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
      when: manual                        # pipeline_approvals; omit this line on an ungated stage
      allow_failure: false                # a manual job blocks the stages behind it
  script:
    - if [ "$(cat plan.exitcode)" != "2" ]; then echo "No changes."; exit 0; fi
    - export ARM_CLIENT_ID="$AZURE_CLIENT_ID" ARM_TENANT_ID="$AZURE_TENANT_ID" ARM_OIDC_TOKEN="$AZURE_OIDC_TOKEN"
    - >
      terraform init
      -backend-config="subscription_id=$TF_STATE_SUBSCRIPTION_ID"
      -backend-config="resource_group_name=$TF_STATE_RESOURCE_GROUP"
      -backend-config="storage_account_name=$TF_STATE_STORAGE_ACCOUNT"
      -backend-config="container_name=$TF_STATE_CONTAINER"
      -backend-config="key=$STATE_KEY_PREFIX/$CI_ENVIRONMENT_NAME.tfstate"
      -backend-config="use_azuread_auth=true"
    - terraform apply tfplan

development:plan:
  extends: .plan
  stage: development
  needs: [validate]
  environment: { name: development, action: prepare }

development:apply:
  extends: .apply
  stage: development
  needs: ["development:plan"]
  environment: { name: development }
  resource_group: development             # one apply per stage at a time, queued
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH   # ungated: no `when: manual`

test:plan:
  extends: .plan
  stage: test
  needs: ["development:apply"]
  environment: { name: test, action: prepare }

test:apply:
  extends: .apply
  stage: test
  needs: ["test:plan"]
  environment: { name: test }
  resource_group: test
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

production:plan:
  extends: .plan
  stage: production
  needs: ["test:apply"]
  environment: { name: production, action: prepare }

production:apply:
  extends: .apply                         # gated: keeps `when: manual` from .apply
  stage: production
  needs: ["production:plan"]
  environment: { name: production }
  resource_group: production
```

A `rules` key in the job replaces the template's, so an ungated apply restates it without
`when: manual`; a gated one inherits. A merge-request pipeline runs `validate` only: no
other job's rule matches it, so no job holds the OIDC token.

## Bicep

Replace the image and the plan/apply scripts; stages, `needs`, `resource_group`, rules and
`id_tokens` are unchanged.

```yaml
default:
  image: mcr.microsoft.com/azure-cli:latest      # pin to a dated tag on render

.login:
  - az login --service-principal --federated-token "$AZURE_OIDC_TOKEN" -u "$AZURE_CLIENT_ID" -t "$AZURE_TENANT_ID" --allow-no-subscriptions
  - az account set --subscription "$AZURE_SUBSCRIPTION_ID"

validate:
  stage: validate
  script:
    - az bicep build --file main.bicep --stdout > /dev/null
    - az bicep lint --file main.bicep
    - for f in main.*.bicepparam; do az bicep build-params --file "$f" --stdout > /dev/null; done

.plan:
  script:
    - |
      f="main.$CI_ENVIRONMENT_NAME.bicepparam"
      [ -f "$f" ] || { echo "$f is missing"; exit 1; }
      if grep -Eq '00000000-0000-0000-0000-000000000000|OPEN-' "$f"; then
        echo "Stage $CI_ENVIRONMENT_NAME still holds placeholder values in $f - answer the open items first."
        exit 1
      fi
    - !reference [.login]
    - >
      az deployment group what-if --resource-group "$AZURE_RESOURCE_GROUP"
      --template-file main.bicep --parameters "main.$CI_ENVIRONMENT_NAME.bicepparam"
      --no-pretty-print > whatif.json
    - n=$(jq '[.changes[] | select(.changeType != "NoChange" and .changeType != "Ignore")] | length' whatif.json)
    - echo "$n" > plan.changes
    - jq -r '.changes[] | select(.changeType != "NoChange" and .changeType != "Ignore") | "\(.changeType)\t\(.resourceId)"' whatif.json
  artifacts:
    paths: [whatif.json, plan.changes]
    expire_in: 1 day

.apply:
  script:
    - if [ "$(cat plan.changes)" = "0" ]; then echo "No changes."; exit 0; fi
    - !reference [.login]
    # The approver read a prediction: what-if is read-only and create redeploys.
    - >
      az deployment group create --name "payments-$CI_ENVIRONMENT_NAME"
      --resource-group "$AZURE_RESOURCE_GROUP" --template-file main.bicep
      --parameters "main.$CI_ENVIRONMENT_NAME.bicepparam"
```

`!reference [.login]` pulls the two login lines into the job's script. The `jq` filter
assumes the `changes[].changeType` shape of `az deployment group what-if --no-pretty-print`;
check it against one real run before relying on the skip.
