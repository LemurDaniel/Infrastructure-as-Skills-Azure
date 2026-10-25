---
description: "A German request with target and module stated. Tests the other direction: context.language is de, the customer-facing text of the spec is German, and the final message is German."
expected_outcome: "infra/infra-spec.yaml with context.language de, German labels in wiring, and a final message in German."
tags: [terraform, language, de]
plugins: ["../../.."]
runs: 3
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Wir brauchen eine Chat-App für unser Support-Team: eine Web-App (App Service), die mit
einem MCP-Server in einem eigenen App Service spricht, einen Storage Account für die
hochgeladenen Dokumente und ein Azure-AI-Foundry-Modell für die Antworten. Terraform mit
AVM-Modulen, Entwicklungsstufe, nur aus dem Firmennetz erreichbar. Region Germany West
Central. Subscription und Resource Group liefert die Pipeline.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults. Kein Diagramm und noch keinen IaC-Code — nur die Spec.
