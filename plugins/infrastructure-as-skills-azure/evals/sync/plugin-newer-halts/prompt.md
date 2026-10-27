---
description: The spec in the repository was written by a newer plugin (plugin_version 99.0.0) than the installed one. Tests that the run halts before changing anything and tells the person to update the plugin.
expected_outcome: infra/infra-spec.yaml untouched with plugin_version 99.0.0 still in it, no CLAUDE.md written, the final message says the plugin is older than the spec and offers the update.
tags: [terraform, development, process, version, extension]
plugins: ["../../.."]
runs: 5
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Im Repo liegt schon eine Spec für den Storage Account der Testdaten. Er soll doch ohne öffentlichen Netzwerkzugang laufen. Ändere das.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults. Kein Diagramm und noch keinen IaC-Code — nur die Spec.
