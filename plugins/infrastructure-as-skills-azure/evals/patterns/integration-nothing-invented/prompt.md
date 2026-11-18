---
description: >-
  An API whose requests are worked off from a queue. Tests that event-integration is chosen, that the queue variant brings the Service Bus and no event topic, that the roles go to the functions' identity and never to the function app, and that nothing the request did not describe is added.
expected_outcome: >-
  infra/infra-spec.yaml with pattern.id event-integration, api-management, function-app__processor, user-assigned-identity__processor, storage-account__host and service-bus; no event-grid-topic, key vault or database; Azure Service Bus Data Sender granted to the identity; the function app's host storage a reference to storage-account__host.
tags: [terraform, pattern, integration, nothing-invented]
plugins: ["../../.."]
runs: 4
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Wir brauchen in Azure eine API mit Warteschlange (Workload "orders", Terraform, mit den
geprüften Bausteinen): Partner schicken Bestellungen an eine API, die Bestellungen werden
als Aufgaben in eine Warteschlange gestellt und im Hintergrund von Funktionen abgearbeitet,
jede genau einmal. Ereignisse für mehrere Empfänger brauchen wir nicht. Die Funktionen sind
in Python geschrieben.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults. Kein Diagramm und noch keinen IaC-Code — nur die Spec.
