---
description: A signed-off Terraform spec with one storage account, rendered with its tests. Tests that every file the render writes carries the comment structure of references/code-structure.md - a header, chapter banners of 75 characters, the root's table of contents in providers.tf, numbered steps over sections - and that the decision comments survive it.
expected_outcome: infra/providers.tf opening with a header and a `Chapters:` list of the root's .tf files; providers.tf and variables.tf each opening a chapter banner; a resource file with a flow chapter and its sections; every banner line exactly 75 characters after the comment mark; `# decision:` comments above the asserts.
tags: [terraform, development, storage, render, code-structure]
plugins: ["../../.."]
runs: 2
max_turns: 80
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Für die Monatsberichte brauchen wir einen Storage Account. Die Spec liegt unter
infra/infra-spec.yaml, sie und das Diagramm sind schon abgenommen. Schreibe jetzt den
Terraform-Code dazu, mit den Tests, ohne Pipeline.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults.
