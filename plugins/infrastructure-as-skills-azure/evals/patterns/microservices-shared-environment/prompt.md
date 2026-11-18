---
description: >-
  Two services as containers, the second a background worker nobody calls. Tests that container-microservices is chosen, that the second service joins the first one's environment instead of getting one of its own, that it has no ingress and no call into it, and that each service pulls its image with an identity of its own.
expected_outcome: >-
  infra/infra-spec.yaml with pattern.id container-microservices, container-apps__api and container-apps__worker, the worker's hosting_environment shared with container-apps__api and its ingress none, AcrPull for both user-assigned identities on the registry, no access line from the first service to the worker.
tags: [terraform, pattern, containers, wiring]
plugins: ["../../.."]
runs: 4
max_turns: 60
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

We need two services as containers in Azure (workload "billing", Terraform, verified
modules): an API that takes requests in, and a second service that works in the
background - it computes the invoices at night and nobody calls it. Both are our own
images.

How to proceed: nobody is here to answer questions. Assume nothing that is not stated
above - required values without an answer go into the spec as open items, defaults apply
to everything else. No diagram and no IaC code yet - only the spec.
