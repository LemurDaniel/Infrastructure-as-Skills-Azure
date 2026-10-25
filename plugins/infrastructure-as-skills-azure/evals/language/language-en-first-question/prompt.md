---
description: "An English request that leaves the target and the module choice open. Tests the first interview message: the target question is asked in English, not as the German wording the skill carries."
expected_outcome: "a first message that asks Terraform or Bicep (and how the code is built) in English, with no German sentence or option text in it."
tags: [language, en, interview]
plugins: ["../../.."]
runs: 3
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

I need a chat app with an MCP server, both in Azure App Services, with a storage account,
RAG and Azure AI Foundry.

Nobody is here to answer follow-up questions in this run; your first message is what gets graded.
