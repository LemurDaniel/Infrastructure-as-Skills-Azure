---
description: >-
  A signed-off Terraform spec whose diagnostics go to the platform's Log Analytics workspace, `{ existing: log_analytics_workspace }` with the development id known and the production id open. Tests that an existing reference renders as an id variable validated on its ARM type, the known id in the development stage file, a placeholder in the production one, and no data source looking the workspace up.
expected_outcome: >-
  infra/ holds a workspace id variable with a validation on Microsoft.OperationalInsights/workspaces; environments/development.tfvars carries law-platform-dev's id, environments/production.tfvars the all-zero GUID placeholder with OPEN-; no data "azurerm_log_analytics_workspace" anywhere, no workspace name or resource group variable; the test passes the id as a variable instead of mocking a data source.
tags: [terraform, development, production, storage, render, reference]
plugins: ["../../.."]
runs: 2
max_turns: 80
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Für die Monatsberichte brauchen wir einen Storage Account, die Logs gehen in den
Workspace der Plattform. Die Spec liegt unter infra/infra-spec.yaml, sie und das Diagramm
sind schon abgenommen. Schreibe jetzt den Terraform-Code dazu, mit den Tests, ohne Pipeline.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults.
