---
description: The repository's CLAUDE.md holds a section of an older plugin (no rev) between the markers, with the team's own text before and after it, and the spec was stamped by an older plugin. Tests that the section is replaced, the team's text stays, and the spec is stamped with the installed version.
expected_outcome: CLAUDE.md with exactly one current section (rev=...), the old sentinel gone, the team's lines before and after intact; the spec changed and its plugin_version no longer 0.0.1.
tags: [terraform, development, process, claude-md, extension]
plugins: ["../../.."]
runs: 3
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Im Repo liegt schon eine Spec für den Storage Account der Testdaten. Er soll doch ohne öffentlichen Netzwerkzugang laufen. Ändere das.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults. Kein Diagramm und noch keinen IaC-Code — nur die Spec.
