---
description: "An English request with target and module stated. Tests that the language is taken from the request: context.language is en, the customer-facing text of the spec is English, and the final message is English."
expected_outcome: "infra/infra-spec.yaml with context.language en, English labels in wiring, no German text anywhere in the spec, and a final message in English."
tags: [terraform, language, en]
plugins: ["../../.."]
runs: 5
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

We need a chat app for our support team: a web app (App Service) that talks to an MCP
server running in its own App Service, a storage account for the uploaded documents, and
an Azure AI Foundry model for the answers. Terraform with AVM modules, development stage,
only reachable from the company network. Region Germany West Central. The pipeline
supplies subscription and resource group.

How this run works: nobody is here to answer follow-up questions. You do not assume what is not stated above — required values without an answer become open items in the spec, everything else takes the defaults. No diagram and no IaC code yet — only the spec.
