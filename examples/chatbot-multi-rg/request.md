# The request

The chatbot of [../chatbot/request.md](../chatbot/request.md), with one addition: the resource
groups. Written for this example to play through the resource-group decisions; nothing here has
been applied.

> Wie bei dem Chatbot, aber nicht alles in eine Ressourcengruppe. Das Netzwerk liegt in
> einer Gruppe, die die Plattform uns gibt (rg-spoke-chatbot-prod-we), die gibt es schon. Die
> Daten (Storage, Cosmos DB) in einer eigenen Gruppe, die Anwendung (Web-App, MCP-Server,
> Function App, Container App, Registry, Foundry, Search) in einer eigenen Gruppe, die
> Überwachung in einer eigenen Gruppe. Alles andere in die Hauptgruppe rg-chatbot-prod-we.
> Die Gruppen außer der des Netzwerks sollt ihr anlegen. Der Speicher, in dem die Function App
> ihren eigenen Zustand ablegt, gehört zur Anwendung, nicht zu den Daten.

What the spec records: `deployment.resource_group_split`, one `resource_group_mode_<role>` per
role (the network group `existing`, the others `create`), the network group's name as
`context.resource_group_name_network`, and `storage-account__host` placed in `application`
(`source: overridden`).
