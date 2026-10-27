---
description: A deployed Bicep root whose Key Vault name predates the <LOCATION> in its pattern, re-rendered for an unrelated change. Tests that the render keeps the deployed name instead of renaming the vault to the current default. The naming.yaml the root gets is written by a script and tested by run_naming_tests.py, not here.
expected_outcome: infra/main.bicep with keyVaultName unchanged ('kv-${env}-${workload}-${uid4}'), blob soft delete at 14 days, naming_convention not custom, blob_soft_delete_days 14 in the spec.
tags: [bicep, development, key-vault, storage, render, naming]
plugins: ["../../.."]
runs: 4
max_turns: 80
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Unsere Infrastruktur für "keepnames" liegt unter infra/ und ist so ausgerollt, die Spec
ist infra/infra-spec.yaml, der Bicep-Code daneben.

Eine Änderung: Gelöschte Blobs im Storage Account sollen 14 Tage aufbewahrt werden statt 7.
Die Änderung ist mit dem Team abgestimmt und abgenommen, ein Diagramm brauchen wir dafür
nicht. Pass die Spec an und render den Bicep-Code neu.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults.
