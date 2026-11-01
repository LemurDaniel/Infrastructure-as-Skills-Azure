---
description: >-
  The logs go to the platform's central Log Analytics workspace, named but without its id. Tests that the interview writes the reference as `{ existing: log_analytics_workspace }` with an open entry whose question carries the name, never the name or an invented id as the value, and creates no workspace of its own.
expected_outcome: >-
  infra/infra-spec.yaml with observability_ownership reference, deployment.diagnostics_destination `{ existing: log_analytics_workspace }` and no id, an open entry for that key naming law-platform-prod; no workspace resource, no workspace name or resource group as a value, no invented resource id.
tags: [terraform, reference, observability, missing-info]
plugins: ["../../.."]
runs: 4
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Ich brauch ein Storage Account für Terraform, da landen die Exporte unseres
Reporting-Tools (Workload "reports"). Die Logs sollen in den zentralen Log Analytics
Workspace von unserem Plattform-Team, der heißt law-platform-prod. Die Resource-ID
hab ich gerade nicht zur Hand.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults. Kein Diagramm und noch keinen IaC-Code — nur die Spec.
