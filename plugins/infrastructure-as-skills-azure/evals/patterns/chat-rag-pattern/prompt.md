---
description: >-
  A chat app over the customer's documents, described without naming a resource. Tests that the interview chooses the ai-chat-rag pattern, records it, and writes the pattern's parts and wiring for the answers given: the company sign-in brings the vault and the secret reference, no chat history brings no database.
expected_outcome: >-
  infra/infra-spec.yaml with pattern.id ai-chat-rag, the parts app-service__chat, foundry, search-service, storage-account and key-vault, no cosmos-db, the search service's roles on the storage account and the model, the sign-in secret referenced from the vault, values the pattern gave marked source pattern.
tags: [terraform, pattern, ai, wiring]
plugins: ["../../.."]
runs: 2
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Wir brauchen in Azure eine Chatapp mit RAG für unseren Kundenservice (Workload "servicechat",
Terraform, mit den geprüften Bausteinen). Die Mitarbeiter stellen Fragen an unsere
Handbücher; die Handbücher spielt ein eigener Prozess ein, die Anwendung liest sie nur.
Vor der Anwendung soll die Firmenanmeldung stehen. Gespräche werden nicht gespeichert.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults. Kein Diagramm und noch keinen IaC-Code — nur die Spec.
