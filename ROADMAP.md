# Roadmap

Where the plugin goes from the prototype it is. `PROGRESS.md` holds the state between
sessions and the one next thing; this file holds the direction, so the next thing can be
read against it. Decided with the owner on 2026-10-18; revised when a phase closes.

## The two paradigms

1. **The interview is for the customer, and the customer sits alone in front of it.**
   No engineer beside them to translate. The questions are about the system they need,
   in their words; the technical decisions are derived, defaulted and *reported*, never
   asked. The plugin is public, so it has to hold for any use case, not for one
   organisation's platform.
2. **Whole systems, not single resources, at a quality that is proven rather than
   claimed.** A web application with its database, identity, secrets and network; a data
   landing; a container stack. Rendered on Azure Verified Modules, tested per decision,
   checked by rules the plugin did not write itself, and deployed for real.

## Where the prototype falls short of them

| Gap | Where it shows | Paradigm |
|---|---|---|
| Every `ask:` is an engineer's question: a subnet prefix, policy-versus-deployment for DNS records, module telemetry | `deployment.yaml`, every `questions.yaml` | 1 |
| One voice for every reader: no `audience` on a question | `question-set-format.md` | 1 |
| Platform facts (vnet, subnet, workspace, DNS scope, mandates) are interviewed per run instead of recorded once per platform | "a pattern skill normally supplies this", with `patterns/` empty | 1, 2 |
| The Phase 4 report is an engineer's report; no customer-readable record of the decisions | `iac-authoring` Phase 4 | 1 |
| Three resources, no pattern, `wiring:` defined by example only | `spec.md`, README status | 2 |
| Quality is asserted, not shown: nothing planned against Azure, nothing applied, Bicep untested, the example still authored, `check_question_set.py` missing, no eval baseline | `PROGRESS.md` Open | 2 |

## The two ideas that carry the plan

### A requirements layer above the question sets

Today: question set → spec. Planned: **requirements → derivation → question sets → spec.**

The customer answers questions about outcomes, in their words. Each answer derives
technical decisions, recorded with `source: requirement` and `derived_from: <requirement id>`:

| Asked of the customer | Derives |
|---|---|
| How bad is it if the system is down for a day? (shrug / annoying / business-critical) | `replication` (LRS / ZRS / GZRS), zone redundancy, which defaults get `confirm_in` |
| May data be gone after an accidental delete? How far back must you be able to go? | `blob_soft_delete_days`, `versioning_enabled`, `point_in_time_restore_days` |
| Who reaches it, and from where? (staff on the company network / partners / the internet) | `network_exposure`, private endpoints |
| Is there anything you have to prove compliance with? (BSI C5, ISO 27001, GDPR, an internal policy) | `mandates`, `key_protection`, `immutability`, retention |
| How long does the data live, and how often is old data read? | `access_tier`, lifecycle rules |
| Must a copy survive deliberate destruction - ransomware, a compromised admin? | a Backup vault and its policies, immutability |
| Where may the data be stored and processed - the country, the EU, anywhere? | the AI deployment type, which geo tiers and replica regions are allowed, the `location` parameter |
| What is this for: trying things out, testing, or real operation? | `environment` |

Everything else is a guardrail default and is reported, not asked. There is no cap on the
customer questions (the budget of six was dropped on 2026-10-24: multiple choice is cheap
for the customer, a guess recorded as their decision is not); the `requirements` group is
asked in full on every run, and a `customer` question that is really a technical choice
with a default is the thing to catch.

### A platform profile per platform

`platform.yaml`, beside `naming.yaml`, written once by whoever owns the platform: landing
zone archetype, the existing vnet and private endpoint subnet, the DNS zone scope and
whether a policy writes the records, the central workspace, the mandates, naming
departures, the telemetry policy. A new resolution step, `source: platform`, between
`carried` and `pattern`.

With it the interview separates into **roles**. Every question carries
`audience: customer | engineer | platform`. The customer answers the requirements, the
profile answers the platform facts, the guardrails answer the rest. An engineer question
with no profile to answer it becomes an `open:` entry with its owner, and is never put to
the customer. There is one audience: the engineer mode planned here was dropped on
2026-10-24 - an engineer states what they know in prose and it is recorded as `stated`.

### Stages, not an environment

Decided on 2026-10-18, after the first renders: one code base is deployed through a
stack of stages — `development`, `test`, `production` by default, a sandbox only when
the customer says so — each from its own parameter file, its own state and, by default,
its own subscription. What differs per stage by nature is a parameter from the stage
file, never a literal in the template; what the stack exists for is parity, relaxed
only for cost outside production and never for security. Every phase below renders
and tests against that shape.

## Phases

### A. Close the foundation

Scaling on an unproven base multiplies the debt. Everything in `PROGRESS.md` Open that
the quality claim rests on:

1. Re-render `private-storage-on-platform` on the AVM modules, both targets, from the
   unchanged spec; settle the test contract in `avm.md`.
2. Write `check_question_set.py`: enum defaults, `depends_on` and `from_deployment`
   targets, `audience`, `renders` against the rendering reference.
3. Bicep tests: assertions on the compiled ARM JSON per decision, the same `# decision:`
   markers, `check_render_coverage.py` reading them.
4. Run the eval suite once and commit `baseline.json`.
5. The first real `terraform plan` and `what-if` against the sandbox subscription the
   owner is setting up.

### B. The customer interview

1. Extend `question-set-format.md`: `audience`, `plain` (a one-line customer-language
   reason per default), `derived_from`.
2. `core/iac-authoring/questions/requirements.yaml`: the questions above, each with
   a `derives:` block mapping answers to decisions.
3. `platform.yaml`: schema, location, resolution step in `iac-authoring` Phase 2.
   Deployment-set questions that are pure platform facts get `audience: platform`.
4. Phase 0 and 3 filter by audience: only `customer` is asked.
5. **The decision document.** `export_decisions.py` renders the spec into a Markdown
   document in the customer's language: because you said X, Y is set; it costs Z and
   protects against W. Offered beside the diagram in Phase 5; after the Markdown, offer a
   Word version once. The spec stays English; the document is for the customer.
6. Evals: a grader on the question count, one on technical vocabulary in the interview's
   questions (CIDR, subnet, policy, telemetry), one `llm` grader on readability with
   concrete PASS and FAIL conditions.

### C. Whole systems

1. **The resources that cover most requests**, each as an AVM call first, a question set
   with `audience`, both rendering references, a diagram icon: `security` (Key Vault,
   user-assigned identity), `compute` (App Service and Container Apps; AKS later), `data`
   (Azure SQL, PostgreSQL Flexible Server), `integration` (Service Bus). That set is what
   most customer systems are built from; the prototype is complete when a request from it
   goes through cleanly, and families beyond it come afterwards.
2. **`wiring:` as a schema**, not an example: the identity graph (who → what → which
   role), the secret flow (app setting → Key Vault reference), the network topology
   (subnet per tier, NSG rules), private endpoint and DNS per resource, diagnostics
   everywhere. `check_spec.py` validates every edge against `resources:`, every role
   against the Azure built-in roles, and that no module reaches into another.
3. **The first pattern, `private-webapp`:** App Service, storage, Key Vault, SQL, private,
   managed identity throughout. Proves composition, pre-answers and wiring. `./patterns/`
   enters `plugin.json` in the same commit.
4. **Requirements choose the pattern.** "A web application with a database, internal"
   selects `private-webapp`; the customer confirms the picture, not the resource list.
5. **The diagram scales:** grouped by tier and subnet, identity edges on their own track,
   a decisions panel per tier rather than per resource.
6. Examples: `greenfield-telemetry` (Bicep, the `create` branches), then `private-webapp`
   (both targets, diffed).

### D. Quality as a gate

1. **PSRule for Azure** on every render: Bicep directly, Terraform through the plan JSON.
   It is Microsoft's rule set for the Well-Architected Framework and it judges the output
   independently of this plugin's own guardrails. Where a guardrail and a rule disagree,
   the disagreement is documented, never suppressed. It is a pipeline gate, not part of
   the plugin: it runs on the GitHub runner (`microsoft/ps-rule`, which brings its own
   PowerShell) here and in the deploy workflow of E1, never on the customer's machine. The
   plugin itself stays Markdown, YAML and Python.
2. **The cross-backend diff automated:** both renders normalised to the decision level,
   failing on any difference not listed as a known asymmetry in the idiom files.
3. **The AVM version drift check** as a scheduled, read-only task that reports what moved.
4. **GitHub Actions in this repository:** the consistency script, `check_spec`,
   `check_question_set`, `terraform test`, `bicep build` and `lint`, render coverage,
   PSRule, the eval suite against the baseline. Nothing merges red.
5. **A consistency number:** the same request five times, the spread of the decisions
   measured and published in the README.

### E. An agent that builds and deploys for real

Automation end to end, against the sandbox subscription:

1. **A deploy workflow the render ships into the consuming repository**
   (`core/iac-rendering/templates/`): OIDC login with a federated credential (no stored
   secret), `plan` or `what-if` on a pull request, `apply` or `az deployment` on merge
   behind an environment approval, PSRule in between. Terraform and Bicep variants.
2. **The agent run:** a request goes in headless (the requirements stated, as the evals
   do), the plugin interviews, writes spec, diagram and decision document, renders, opens
   a pull request; the workflow plans; the agent reads the plan, deploys into the
   sandbox, verifies the resources against the spec through the Azure API, and destroys.
   One run is the proof the README can point at; a scheduled run is the regression test
   for the whole pipeline.
3. The sandbox subscription, its federated credential and the resource group policy that
   fences it: the owner's setup, tracked in `PROGRESS.md`.

## Order

```
A1 AVM render ──┬─> A3 Bicep tests ──> D2 cross-backend diff
                └─> C1 resources ──> C3 pattern ──> C6 examples ──> E2 agent run
A2 check_question_set ──> B1 format ──> B2 requirements ──> B4 role interview ──> B5 document
B3 platform profile ────────────────────────────────────────┘
A4 eval baseline ──> B6 / C evals
A5 plan against Azure ──> D1 PSRule ──> D4 CI ──> E1 deploy workflow
```

Start with A1 and A2 in parallel. Then B3 and B1, which are small and change the
interview immediately. Then C1 `security` and `compute`, then C3. D runs alongside from
A5; E follows D4 and C6.
