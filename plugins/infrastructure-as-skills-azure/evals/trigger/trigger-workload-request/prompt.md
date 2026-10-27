---
description: A workload-shaped request that names no resource and no target. Tests that the plugin triggers on what the system does, not only on resource names.
expected_outcome: the iac-authoring skill fires, the run treats the request as an Azure infrastructure task (interview, spec) and writes no IaC code or generic architecture advice.
tags: [trigger, interview]
plugins: ["../../.."]
runs: 4
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Ich brauche eine Chatapp in Azure mit RAG.

Es ist niemand da, der Rückfragen beantwortet; deine erste Nachricht wird bewertet. Kein
Diagramm und noch keinen IaC-Code.
