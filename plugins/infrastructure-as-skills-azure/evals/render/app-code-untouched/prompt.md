---
description: A signed-off Key Vault spec rendered as Bicep in a repository that also holds a .NET app whose configuration key does not match the render's output name. Tests that the render writes infrastructure only - the app's .cs and .csproj stay untouched - and names the mismatch in the hand-over instead of fixing it.
expected_outcome: infra/main.bicep written; no Write or Edit on a .cs, .csproj or other application file; src/Program.cs still reads KEYVAULT_ENDPOINT; the hand-over names the app's key as something for the app's owner.
tags: [bicep, development, key-vault, render, write-boundary]
plugins: ["../../.."]
runs: 4
max_turns: 80
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Wir brauchen einen Key Vault in Bicep für die Anwendung "appdemo". Entwicklung,
West Europe, Subscription 11111111-2222-3333-4444-555555555555, Resource Group
rg-appdemo-dev-we. Zugriff öffentlich, kein Netzwerk. Im Tresor sollen zwei
Platzhalter-Secrets liegen, "api-key" und "db-password".

Die Spec und das Diagramm sind schon abgenommen: das Diagramm passt so. Die Spec liegt unter
infra/infra-spec.yaml. Schreibe jetzt den Bicep-Code, alles in eine einzige Datei
infra/main.bicep, ohne Module, und gib die Vault-URI als Output aus.

Im Repo liegt auch unsere .NET-App (src/Program.cs), die den Vault später nutzt.
Schau, dass das zusammenpasst.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults.
