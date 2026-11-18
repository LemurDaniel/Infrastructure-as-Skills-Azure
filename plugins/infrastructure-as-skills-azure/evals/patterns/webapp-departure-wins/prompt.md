---
description: >-
  A web application with PostgreSQL and file storage, and one stated departure from the pattern: the application only reads the files. Tests that private-webapp is chosen with the right database part, that the customer's word wins over the pattern's role, and that the changed role list no longer claims the pattern as its source.
expected_outcome: >-
  infra/infra-spec.yaml with pattern.id private-webapp, postgresql-flexible-server and no sql-database, a storage-account whose role for app-service__web is Storage Blob Data Reader and nowhere Contributor, wiring.role_assignments not source pattern, no key-vault.
tags: [terraform, pattern, webapp, departure]
plugins: ["../../.."]
runs: 4
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

We need a web application with a database in Azure - an internal portal for our field
staff (workload "fieldportal", Terraform, verified modules). The application is written
for PostgreSQL. It also shows files - manuals and price lists - but it must only ever read
them; another team loads them. The application handles the sign-in itself.

How to proceed: nobody is here to answer questions. Assume nothing that is not stated
above - required values without an answer go into the spec as open items, defaults apply
to everything else. No diagram and no IaC code yet - only the spec.
