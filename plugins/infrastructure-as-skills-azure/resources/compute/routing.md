# Azure compute resources

A resource family, reached from the [azure-resources](../../core/azure-resources/SKILL.md)
skill. Routing table - the request picks the question set:

| Request mentions | Question set | Notes |
|---|---|---|
| App Service, web app, App Service plan, webapp, azurewebsites, deployment slot, staging slot | `app-service/questions.yaml` | [notes](app-service/notes.md) - slots are its `slots` group |
| function app, Azure Functions, Flex Consumption | `function-app/questions.yaml` | [notes](function-app/notes.md) - same module as App Service, `kind: functionapp` |
| Container Apps, container app environment, containerapp | `container-apps/questions.yaml` | [notes](container-apps/notes.md) - environment and one app |
| Container Registry, ACR, image registry | `container-registry/questions.yaml` | [notes](container-registry/notes.md) |
| AKS, Kubernetes, managed cluster, node pool, kubernetes cluster | `aks/questions.yaml` | [notes](aks/notes.md) - cluster with one system and one user pool |
| Static Web App, static site, SWA, azurestaticapps | `static-web-app/questions.yaml` | [notes](static-web-app/notes.md) |
| Container Instances, ACI, container group, container instance | `container-instances/questions.yaml` | [notes](container-instances/notes.md) - one group, one container |
| virtual machine, VM, Linux VM, Windows VM, Azure VM, server, Entra login, trusted launch, encryption at host | `virtual-machine/questions.yaml` | [notes](virtual-machine/notes.md) - one machine; Entra sign-in, backup link and auto-shutdown included |
| managed disk, data disk, OS disk, disk encryption set, Premium SSD, ZRS disk | `managed-disk/questions.yaml` | [notes](managed-disk/notes.md) - a standalone disk; a machine's own disks are in the VM set |
| availability set, fault domain, update domain, proximity placement group, PPG | `availability-set/questions.yaml` | [notes](availability-set/notes.md) - the PPG is a question group of this set |
| scale set, VMSS, Flexible orchestration, instance repair, rolling upgrade | `virtual-machine-scale-set/questions.yaml` | [notes](virtual-machine-scale-set/notes.md) - Flexible by default |
| autoscale, custom domain | *not yet written* | Decisions of an existing app; listed as boundaries of the App Service set |

When a question set does not exist yet, say so rather than improvising one. Fall back to
[the guardrails](../../core/iac-authoring/references/guardrails.md), generate from those
rules, and record in the spec that no question set backed it.

## Then

1. [iac-authoring](../../core/iac-authoring/SKILL.md) - the interview protocol, and
   [the deployment set](../../core/iac-authoring/questions/deployment.yaml), which already
   answers exposure, network ownership and the diagnostics destination before this set runs
2. [iac-rendering](../../core/iac-rendering/SKILL.md) - the spec into Terraform or Bicep

## True for the whole family

**Which set hosts the application is the deployment set's answer, not this family's.**
`deployment.app_runtime` and `app_containers` route it: code -> `app-service` (event-driven
parts -> `function-app` in the same language), one container -> `app-service` for containers,
several -> `container-apps`. A request that names the service is `stated` and wins; otherwise no
set is chosen before the technology is known.

**Compute is where the other families' decisions land.** An app is reached through a
private endpoint and reaches out through a network integration; it logs to the workspace;
it holds an identity that other resources grant roles to. Almost every decision in an
App Service set is inherited from the deployment set or derived from a requirement, and
the few that are the app's own (size, health check) are an engineer's. The runtime comes from
`deployment.app_runtime`; a customer is asked nothing new by this family.

**Inbound and outbound are separate features** with separate subnets: the private endpoint
sits in the platform's endpoint subnet, the VNet integration in a subnet delegated to the
plan. Asking only one is the common half-answer.

**The plan is the cost and the app is the workload.** Size, zone redundancy and instance
count belong to the plan and are billed per instance whether or not the app is busy; the
app's decisions cost nothing by themselves. A plan can host several apps, and this set
renders one plan per app - sharing a plan is wiring, owned by a pattern.
