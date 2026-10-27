---
description: A Key Vault with two secret placeholders, rendered as Bicep. Tests that every placeholder carries @onlyIfNotExists() - written once, never over a value somebody set - and that the render has no lookup of existing secrets.
expected_outcome: infra/main.bicep with a secret resource per placeholder under @onlyIfNotExists(), no existingSecretNames parameter, no condition on a lookup, no secret value in the file.
tags: [bicep, development, key-vault, render]
plugins: ["../../.."]
runs: 4
max_turns: 80
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Wir brauchen einen Key Vault in Bicep für die Anwendung "secretdemo". Entwicklung,
West Europe, Subscription 11111111-2222-3333-4444-555555555555, Resource Group
rg-secretdemo-dev-we. Zugriff öffentlich, kein Netzwerk.

Im Tresor sollen zwei Platzhalter-Secrets liegen, "api-key" und "db-password". Die echten
Werte trägt später jemand von Hand ein; ein erneutes Ausrollen darf sie nicht überschreiben.

Die Spec und das Diagramm sind schon abgenommen: das Diagramm passt so. Die Spec liegt unter
infra/infra-spec.yaml. Schreibe jetzt den
Bicep-Code, alles in eine einzige Datei infra/main.bicep, ohne Module.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults.
