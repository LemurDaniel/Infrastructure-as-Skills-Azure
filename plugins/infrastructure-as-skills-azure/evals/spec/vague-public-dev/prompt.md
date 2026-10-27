---
description: A short, underspecified request - dev, public, no subscription, no resource group, no region, no workspace. Tests that missing values become open items instead of plausible inventions.
expected_outcome: infra/infra-spec.yaml with public exposure and no network, open entries for subscription, resource group, region and the diagnostics workspace, no invented ids or names; the final message says the spec is not applyable yet.
tags: [terraform, development, public, missing-info]
plugins: ["../../.."]
runs: 2
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Ich brauch ein Storage Account für Terraform, für die Assets unserer Doku-Website
(Workload "docs"), Entwicklungsumgebung. Öffentlich erreichbar ist okay, ist eh nur
Testkram. Logs bitte nach Log Analytics.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults. Kein Diagramm und noch keinen IaC-Code — nur die Spec.
