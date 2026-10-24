---
description: Outcome pilot - same request as the spec case private-storage-on-platform, but graded on the Terraform a user receives, not on the spec. Run with and without the plugin to measure what the skills add.
expected_outcome: Terraform under infra/ (any layout) with one private storage account, referenced network and workspace, no invented values.
tags: [terraform, production, private, reference, outcome, ablation]
plugins: ["../../.."]
runs: 3
max_turns: 80
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Wir brauchen für die Rechnungsablage der Buchhaltung einen Storage Account, in Terraform.
Workload heißt "invoicing", Produktion, West Europe. Subscription
11111111-2222-3333-4444-555555555555, Resource Group rg-invoicing-prod-we.

Zugriff nur aus dem Firmennetz: Es gibt ein bestehendes Hub-VNet vnet-hub-prod-we in der
Resource Group rg-network-prod-we, die Private Endpoints kommen dort ins vorhandene Subnet
snet-privatelink. Die Logs gehen in unseren zentralen Workspace log-platform-prod-we in
rg-observability-prod-we. Wir unterliegen BSI C5.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an. Schreibe den Terraform-Code unter infra/ - so, wie du es in einem echten
Repository aufbauen würdest.
