# `platform.yaml` — the platform profile

The facts no customer knows and no interview should ask: which landing zone a workload
goes into, which hub network and subnet carry its private endpoints, who writes the DNS
records, which workspace receives the logs, whether the modules may phone home. They
belong to the organisation's platform, they are the same for every deployment on it,
and the person who knows them is the platform or DevOps engineer — not the person
describing the system they need.

So they are written **once, by that engineer**, into `platform.yaml`, and every interview
on that platform reads them. The customer never sees the questions.

## Shape

The keys are the ids of the deployment-set questions with `resolved_by: platform`
([questions/deployment.yaml](../questions/deployment.yaml)); the values are what those
questions would take. Nothing else goes in — a key the deployment set does not have, or
one without `resolved_by: platform`, is rejected by the check.

```yaml
schema_version: 1

# Who maintains this file, so a wrong value has an owner.
platform:
  id: corp-platform-prod            # free text; appears in the spec and the handover
  owner: platform team              # free text

# Deployment-set answers, keyed by question id. Every value enters the interview as
# source: platform.
landing_zone: corp
naming_convention: default
module_telemetry: enabled

network_ownership: reference
existing_vnet:
  name: vnet-hub-prod-we
  resource_group_name: rg-network-prod-we
private_endpoint_subnet: snet-privatelink

private_dns_ownership: platform
private_dns_records: policy

observability_ownership: reference
diagnostics_destination:
  name: log-platform-prod-we
  resource_group_name: rg-observability-prod-we
```

A platform fact that differs between the stages — the hub, the subnet, the workspace of
each stage's subscription — is a map keyed by stage, with the stages the engineer knows:

```yaml
existing_vnet:
  development: { name: vnet-hub-dev-we, resource_group_name: rg-network-dev-we }
  production: { name: vnet-hub-prod-we, resource_group_name: rg-network-prod-we }
```

A stage the map leaves out is an `open:` entry naming that stage, owned by the platform
team. A profile does not have to answer every platform question. One that says only
`landing_zone: standalone` is valid: the rest resolves as the deployment set describes.
What it does not answer and nobody else can is an `open:` entry in the spec, with the
platform owner named — never a question put to the customer.

A copy to start from is [platform.template.yaml](platform.template.yaml), every key
commented.

## Where it lives

Beside `infra-spec.yaml` and `naming.yaml`, in the IaC root — the same lookup as the
spec ([spec.md](spec.md#where-it-lives)). One profile per root; a root is on one platform.

| Found | Then |
|---|---|
| None | No platform facts. Platform questions resolve from their defaults where they have one; the rest become `open:` entries owned by the platform team. Say in the first message that no profile exists and where one would go |
| One | Read it before the deployment set. Every value it carries enters resolution as `platform` |
| In the user's words, a departure from it | The user wins, recorded `overridden` with the profile value named — and say what the departure implies, as with a pattern |

The interview never writes `platform.yaml`. It is the engineer's file; a run that invents
one has invented a platform. When the user is that engineer and states platform facts in
the interview, offer once to write them into the profile so the next run on the same
platform does not ask again — and only write it when they say yes.

## Precedence

`platform` sits between `carried` and `pattern`
([iac-authoring, Phase 2](../SKILL.md#phase-2--resolve-the-deployment-set-then-every-resource-question)):
a decided and possibly deployed value outranks the profile, the profile outranks what a
pattern presumes about the platform, and both outrank the question set's default.

## Validate

```powershell
python3 <plugin>/core/iac-authoring/scripts/check_question_set.py --platform ./platform.yaml
```

Checks that every key is a deployment-set question with `resolved_by: platform`, that enum
values are within the question's `values`, and that a `ref` value carries what the
deployment set asks for (a name and a resource group, not a resource id).
