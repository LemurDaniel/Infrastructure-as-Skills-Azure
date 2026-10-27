---
description: A request that states all five customer requirements in plain words. Tests that each lands in the deployment requirements group with the right value and that the resource decisions derive from them.
expected_outcome: infra/infra-spec.yaml with outage_impact critical, data_loss_tolerance three_months, data_access_pattern archive, backup_isolation immutable and data_residency country, and an access tier derived from the access pattern.
tags: [terraform, production, requirements]
plugins: ["../../.."]
runs: 3
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Ich brauch ein Storage Account für Terraform, Workload "archive", Produktion, standalone,
Germany West Central. Das ist unser Revisionsarchiv für Rechnungen. Fällt es einen Tag aus,
steht die Buchhaltung — das wäre geschäftskritisch. Wird etwas versehentlich gelöscht oder
überschrieben, müssen wir bis zu drei Monate zurückkommen. Die Daten werden nach dem
Schreiben fast nie gelesen, nur aufbewahrt, weil es das Gesetz verlangt. Es muss eine Kopie
geben, die auch ein Admin oder ein Angreifer nicht ändern oder löschen kann. Und die Daten
dürfen Deutschland nicht verlassen.

Zum Ablauf: Es ist niemand da, der Rückfragen beantwortet. Was oben nicht steht, nimmst du
nicht an — Pflichtwerte ohne Antwort kommen als offene Punkte in die Spec, für alles andere
gelten die Defaults. Kein Diagramm und noch keinen IaC-Code — nur die Spec.
