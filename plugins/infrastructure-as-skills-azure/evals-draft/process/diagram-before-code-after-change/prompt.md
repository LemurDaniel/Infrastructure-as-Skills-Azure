---
description: A spec is written, then changed in the same request, and code is asked for. Tests that the change is drawn and signed off before any Terraform exists - the order spec, diagram, sign-off, render holds after a change of the spec.
expected_outcome: infra/infra-spec.yaml with the changed decision, the iac-diagram skill fired, no .tf written, the final message asks for the diagram's sign-off.
tags: [terraform, development, process, diagram, extension]
plugins: ["../../.."]
runs: 3
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Wir brauchen einen Storage Account für Testdaten, in Terraform. Workload heißt "testdata",
Entwicklung, West Europe. Subscription 11111111-2222-3333-4444-555555555555, Resource
Group rg-testdata-dev-we. Zugriff öffentlich, kein Netzwerk.

Lege die Spec an. Ändere danach die Spec direkt: der Zugriff soll doch ohne öffentlichen
Netzwerkzugang laufen. Dann schreibe den Terraform-Code unter infra/.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an.
