---
description: A user who does not want modules. Tests that the stated departure from the AVM default is recorded as deployment.module_source authored and not overwritten per resource.
expected_outcome: infra/infra-spec.yaml with deployment.module_source authored, no avm implementation anywhere, a Terraform target and no code.
tags: [terraform, development, module-source]
plugins: ["../../.."]
runs: 3
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Ich brauch ein Storage Account für Terraform, Workload "reports", Entwicklungsumgebung,
standalone, nur privat erreichbar. Bitte keine fertigen Module, auch nicht die von
Microsoft: die Ressourcen sollen einzeln ausgeschrieben sein, wir wollen jede Zeile selbst
reviewen.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults. Kein Diagramm und noch keinen IaC-Code — nur die Spec.
