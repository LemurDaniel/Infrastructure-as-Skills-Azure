---
description: Working mode Subagents is chosen up front. Tests that the main session runs the diagram script itself and starts the review agent as an Agent call of its own, not folded into a brief.
expected_outcome: infra/infra-spec.yaml written, at least one Agent call, the review (a fix agent only if the review found an error), its brief names the PNG and the spec, no .tf written.
tags: [terraform, development, process, diagram, subagents]
plugins: ["../../.."]
runs: 3
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Agent]
---

Wir brauchen einen Storage Account für Testdaten, in Terraform. Workload heißt "testdata",
Entwicklung, West Europe. Subscription 11111111-2222-3333-4444-555555555555, Resource
Group rg-testdata-dev-we. Zugriff öffentlich, kein Netzwerk.

Arbeitsmodus: Mit Subagenten (die Antwort auf die Frage nach dem Ablauf). Lege die Spec an
und zeichne das Diagramm. Noch kein Code.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an.
