---
description: Three resources and no word about who talks to whom. Tests that the spec does not invent a call - an invented line in a picture the customer signs off on is a decision nobody made.
expected_outcome: infra/infra-spec.yaml with the three resources and no wiring.access entry and no role assignment between them; SQL Server, which has no question set, is not silently improvised; no Bicep written.
tags: [bicep, staging, diagram, wiring, missing-info]
plugins: ["../../.."]
runs: 3
max_turns: 80
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Für unsere neue Bestell-App brauchen wir in Bicep einen App Service, einen Storage Account
und eine SQL-Datenbank. Region West Europe, Stufe Staging. Mehr steht noch nicht fest.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults. Kein Diagramm und noch keinen IaC-Code — nur die Spec.
