# The request

Written for this example: the first run of the whole flow with a customer in the
conversation - the owner, answering as the customer - and both loops with subagents
(2026-10-24). A small chat environment for development, on one throwaway stage, public,
authored Terraform, deployed by hand. Everything here is a placeholder; nothing has been
applied.

Phase 0, the three structured questions: **Terraform**, **einzelne Ressourcen** (authored,
no AVM), **Naming-Werkzeug des Plugins** (the `LemurDaniel/naming` provider). Then the
description:

> Ich will zu Entwicklungszwecken eine kleine Chatumgebung mit Foundry und persistentem
> Storage erstellen. Der Login soll mit Client Secret über eine Entra ID App laufen. Auf dem
> App Service läuft ein Docker-Container mit einer kleinen Anwendung.

Phase 3, the one batch, answered by the customer: Stufen **Sandbox** · Zugang **öffentlich**
· Ausrollen **von Hand** · Datenstandort **nur in der EU** · Ausfall **verkraftbar** ·
Datenverlust **eine Woche** · Backup **nein** (nur innerhalb des Systems) · Nutzung
**laufend** · Vorgaben **keine** · Protokolle **30 Tage** (asked because a standalone
deployment builds its own workspace).

Phase 5, the diagram loop: after the first picture the customer added

> Ich glaube wir brauchen noch einen Search Service für RAG

and then objected to the picture itself ("die Diagramm-Pfeile überlappen sich"), which the
review agent and the diagram agent resolved by hand before the sign-off. After the render
the owner asked for two corrections that the sandbox rule written on the same day now makes
by itself: the App Service plan at B1 instead of P1v3 and the search service at `basic`
(`non_production_default`, forced by `environments: [sandbox]`), and the key vault without
purge protection and with the shortest soft-delete window, recorded `overridden` with the
reason.
