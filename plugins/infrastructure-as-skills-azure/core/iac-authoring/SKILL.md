---
name: iac-authoring
description: The entry point for Azure infrastructure as Terraform or Bicep. Use whenever someone wants something built, changed or reviewed in Azure, whether they name the workload (chat app, chatbot, RAG, web app, API, data platform, landing zone) or a resource, or ask for Azure Infrastruktur, Terraform-Code, Bicep-Code, an infra-spec.yaml, or why a default was chosen. Read before authoring any Azure resource or pattern.
---

# Authoring infrastructure from a question set

Each resource family under `resources/` holds one directory per resource, and its
`questions.yaml` carries the decisions that resource forces, grouped by concern. This file is the
protocol for turning a question set into a spec, and the spec into code. Follow it rather
than improvising — the value of the plugin is that two runs of the same skill ask the same
things and record them the same way.

This skill is the **entry point**: its description carries what people type when they
want Azure infrastructure — the targets, the workload words ("chat app with RAG" / "Chatapp mit RAG", web app,
API, landing zone) and a few resource names — because a request names what the system
does far more often than the resources it needs ("a chat app in Azure with RAG" / "eine Chatapp in Azure mit RAG"
must match, and a resource list alone does not). Behind it, three units kept apart on purpose: the
[azure-resources](../azure-resources/SKILL.md) skill carries the **resource terms** and
routes to the family, the family is the **routing** unit, the question set the
**knowledge** unit. They are separate because the skill listing has a shared character
budget, and a description that overflows it is dropped silently — the skill stays
installed and stops matching. A skill per resource would spend the budget at once; a skill
per family spent it by the sixth family; and the resource list lives in azure-resources so
that it can grow without crowding out this description.

## The pipeline

```
question set  ──interview──>  infra-spec.yaml  ──draw──>  infra-diagram.drawio.png  ──sign-off──>  render  ──validate──>  explained plan
                 [here]                          [iac-diagram]        (loop with the customer)    [iac-rendering]
```

The picture comes before the code, always: the customer signs off on the diagram, not on
the spec, and the render starts only once they have. This holds for every change of the
spec, including one made by editing it directly: redraw, then render.

The spec in the middle is the load-bearing part. It is the handover interface, not a
by-product: a backend renders *from* it, and the same spec gives Terraform and Bicep the
same decisions. Never generate code directly from the interview.

## Before anything — find an existing spec

Search the repository for `**/infra-spec.yaml` first — the customer's repository, never
the plugin's own directory: nothing under it, its tests and fixtures included, is a
starting spec, a template or something to copy from, whatever its name resembles. If one
exists, this run **extends** it rather than starting over: its decisions are carried, Phase 0 asks what should be added
or changed, and only the delta is asked and reported. If none exists, the spec this run
writes goes into the repository's IaC root, or `infra/` when there is none, and is
committed with the code — it is what the next run extends. The rules for both, and for
several roots, are in [references/spec.md](references/spec.md#where-it-lives).

**Version gate, first.** Where a spec was found, run `python <plugin>/core/iac-authoring/scripts/check_plugin_version.py <spec>`
(without a shell: read `version` in `<plugin>/.claude-plugin/plugin.json` and `spec.plugin_version`
and compare them as numbers yourself; a spec without the field is not held back).
Exit 3 - or a spec version higher than the installed one - means the spec was written by a newer plugin than the installed one: **stop** - no sync, no
question of the interview, nothing written or rendered. Ask once with AskUserQuestion, in
`context.language`: the spec's and the installed version, and "Plugin jetzt aktualisieren?" / "Update the plugin now?" with
two options (*Ja, jetzt aktualisieren* / *Yes, update now*; *Nein, ich aktualisiere selbst* /
*No, I will update it myself*). The yes runs
`claude plugin update infrastructure-as-skills-azure@infrastructure-as-skills-azure` (`claude plugin list`
shows the id if that one is unknown; where `claude` is not on `PATH`, name the command instead of
running it), then says that Claude Code must be restarted for the update to load and the request
repeated - and stops. *Nein, ich aktualisiere selbst* names the command and stops. There is no
third option that carries on with the older plugin, and `plugin_version` is never lowered. Whatever
this run writes into the spec sets `spec.plugin_version` to the installed version
(`.claude-plugin/plugin.json`).

Then bring the repository's `CLAUDE.md` section up to date, before
anything else is asked: `python <plugin>/core/iac-rendering/scripts/sync_claude_md.py
<repo-root> --root <iac-root> --write`. It replaces only an older plugin section, leaves a
newer one alone and never fails the run (without a shell, apply the same rules by hand with
Read and Edit, from [claude-md-block.md](../iac-rendering/references/claude-md-block.md)); say in one line what it did. A section **newer**
than this plugin means the plugin is out of date: tell the customer so in the first message,
in `context.language` ("Das Plugin ist älter als der letzte Lauf in diesem Repo - bitte
aktualisieren" / "The plugin is older than the last run in this repo - please update"), and
carry on. It changes no code, so it is its own commit.

Look for `platform.yaml` beside it in the same search. It is the platform engineer's
profile — landing zone, hub network and subnet, DNS, workspace, telemetry — and every
value in it answers a deployment-set question with `resolved_by: platform` before anyone is
asked. Say in the first message whether one was found. Never write it from an interview:
[references/platform.md](references/platform.md).

## Who is in the interview — the customer, always

The person answering is **the customer**: someone who can say what the system is for,
who uses it and how bad an outage or a loss would be, and who did not come to answer
questions about subnets. There is one person in the interview and no second mode. A question's `resolved_by`
([question-set-format](references/question-set-format.md#who-resolves-it-resolved_by))
decides what happens to it:

| `resolved_by` | What happens |
|---|---|
| `interview` | Put to the person: the module choice and the naming mechanism (asked first), the deployment set's context, posture, mandates and `requirements` group, and any resource question that carries it |
| `platform` | Read from `platform.yaml`, else its default; a `required` one with no profile is an `open:` entry owned by the platform team |
| *(absent)* | Its default, or derived from a requirement; a `required` one nobody can default is an `open:` entry owned by the workload's engineer |

Say so in the first message: "Ich frage dich nur, was das System braucht; die
technischen Entscheidungen setze ich nach den Vorgaben und zeige sie dir am Ende." / "I only
ask what the system needs; I set the technical decisions from the baseline and show them to
you at the end." An
engineer in front of the plugin gets the same questions. What they know beyond them they
say in prose - "ZRS", "subnet snet-pe-01", "TLS 1.2 is enough" ("TLS 1.2 reicht") - and Phase 0 records it as
`stated`, which outranks every default; what they want changed afterwards is an
`overridden` value in the spec, not a second interview.

No question with Azure vocabulary reaches the person, whatever it would cost to default
it. The cost of a wrong default is a line in Phase 4 that the person can object to; the
cost of a subnet question is a person who stops answering.

## Phase 0 — Ask how the code is built, then what is being built

**Everything said to the person is said in their language - from the very first question.**
Take it from the request ("I need a chat app..." is `en`, "Ich brauche..." is `de`) before
anything is asked; it becomes `context.language`. The blocks in this skill that are written
in German - the target, module and naming questions, the description prompt, the design
tick list, the working-mode question, the sign-off, the opening line - come with an English
block beside them. Use the block that matches `context.language`; for any other language
translate the English one, with the same options and the same meaning. Never put the German
text in front of someone who wrote English. Option labels and the `AskUserQuestion` header
follow the same rule.

Three structured questions open the interview, each through `AskUserQuestion`, each
skipped when the repository or the request already answers it; then one open question in
prose. In this order, because each one decides how the next is worded.

**The first question is the target**: Terraform or Bicep. The repository answers it when
it can - `*.tf` or `.terraform.lock.hcl` present → Terraform, `*.bicep` or
`bicepconfig.json` present → Bicep, and a carried `infra-spec.yaml` has it - and then it is
not asked. Both or neither → ask, once, two options and none marked recommended:

```
In welcher Sprache soll die Infrastruktur beschrieben werden?
  1. Terraform - Herstellerunabhängig, eine Sprache für Azure und alles andere; der Stand
     wird in einer State-Datei geführt
  2. Bicep - Microsofts eigene Sprache für Azure, ohne State-Datei; der Stand ist, was in
     Azure liegt
```

```
Which language should describe the infrastructure?
  1. Terraform - Vendor-neutral, one language for Azure and everything else; the state is
     kept in a state file
  2. Bicep - Microsoft's own language for Azure, no state file; the state is whatever is in
     Azure
```

It comes first because the naming question below exists only for Terraform, and because
the layout (Phase 1) and every rendering reference read it.

**The second question is the module choice**, before the description and before any resource
question: `deployment.module_source` — the code built from Azure Verified Modules (`avm`), or
from resources written out one by one (`authored`). It comes first because it decides what
every later decision renders to, and because it is the one choice a person can make without
knowing a resource. Ask it through `AskUserQuestion`, `avm` first and marked recommended;
when the repository already holds authored resource blocks, put `authored` first instead.
Word it without the product name in the label:

```
Wie soll der Code gebaut werden?
  1. Geprüfte Bausteine (empfohlen) - Aus Microsofts getesteten, gepflegten Bausteinen
     (Azure Verified Modules) - in Terraform und Bicep gleich aufgebaut
  2. Einzelne Ressourcen - Aus einzeln ausgeschriebenen Ressourcen - jede Zeile im eigenen
     Review, dafür mehr Code, den ihr selbst pflegt
```

```
How should the code be built?
  1. Verified building blocks (recommended) - From Microsoft's tested, maintained building
     blocks (Azure Verified Modules) - built the same way in Terraform and Bicep
  2. Individual resources - Written out resource by resource - every line in its own
     review, but more code that you maintain yourselves
```

**Skip it when it
is already answered**: the user said it ("without modules" / "ohne Module", "with AVM" / "mit AVM"), or a carried
`infra-spec.yaml` has it. A resource whose type has no Azure Verified Module renders
authored whatever the answer, recorded per module; say so when the person chose `avm`.

**The third question, for a Terraform target only, is the naming
mechanism**: `deployment.naming_source`. Ask it right after the module choice through
`AskUserQuestion`, with three options and **none marked recommended**: the
`LemurDaniel/naming` provider, the `Azure/naming/azurerm` module, or a custom mechanism
(the organisation's own locals or module). Word it like this, with the product names in
brackets - the one place a product name is allowed, because the options are products:

```
Wie sollen die Ressourcennamen erzeugt werden?
  1. Naming-Werkzeug des Plugins - Gesteuert über eine Namensdatei (naming.yaml), die ihr
     anpassen könnt (LemurDaniel/naming Provider)
  2. Microsofts Naming-Modul - Fertiges Modul mit CAF-Abkürzungen, keine eigene Namensdatei
     (Azure/naming/azurerm)
  3. Eigener Mechanismus - Der Mechanismus, den eure Organisation schon nutzt (eigene
     locals oder eigenes Modul)
```

```
How should the resource names be generated?
  1. The plugin's naming tool - Driven by a naming file (naming.yaml) that you can adapt
     (LemurDaniel/naming provider)
  2. Microsoft's naming module - Ready-made module with CAF abbreviations, no naming file of
     your own (Azure/naming/azurerm)
  3. Custom mechanism - The mechanism your organisation already uses (your own locals or
     your own module)
```

A Bicep target is not asked: it always assembles names from vars.

**Skip it when it is already answered**: the user said it, a carried spec has it, or the
repository already uses one - a naming provider block, a naming module call or naming
locals answers it. Which mechanism renders what is in
[naming.md](../iac-rendering/references/naming.md#the-mechanism).

Then the interview opens with one open question, not with the question set. Let the user
describe what they are building, and let that description answer as much as it can.
Only what it leaves open is asked afterwards.

The reason is the order of cost. A paragraph of prose is cheap to write and typically
settles the environment, the region, what the thing is for, who reaches it and from where,
and whether a mandate applies — half the deployment set, before a single structured
question. Starting with the question set instead asks those things one field at a time,
and asks some that the user would have answered in passing.

**Skip it when the request already is that description.** "Storage for the accounting
department's invoice archive, prod in West Europe, company network only, BSI C5" (German:
"Storage für die Rechnungsablage der Buchhaltung, Prod in West Europe, nur aus dem
Firmennetz, BSI C5") needs no opening question. A bare resource name — "I need a storage
account for terraform" (German: "ich brauch ein storage account für terraform") — is not a
description; it names the resource and nothing about the system around it.

Ask in plain text, not through `AskUserQuestion`: the point is free prose, and options
would turn it back into the structured interview it precedes. Give the user a short list
of what is worth mentioning, so the description lands on the questions that matter. The
list is the `requirements` group in prose and nothing technical:

```
Beschreib kurz, was ihr braucht. Hilfreich ist alles davon, nichts davon ist Pflicht:
  - Wofür ist es da? Es gibt eine Entwicklungs-, eine Test- und eine Produktionsstufe,
    außer ihr sagt etwas anderes (nur eine Sandbox zum Ausprobieren, eine Stufe mehr)
  - Wer arbeitet damit, und von wo (nur Mitarbeiter im Firmennetz, Partner, das Internet)?
  - Wie schlimm wäre es, wenn es einen Tag nicht erreichbar ist?
  - Wie weit zurück müsst ihr kommen, wenn jemand versehentlich etwas löscht?
  - Muss eine Kopie überleben, wenn jemand die Daten absichtlich zerstört (Ransomware,
    ein gekapertes Admin-Konto)?
  - Wo dürfen die Daten liegen und verarbeitet werden: nur im Land, nur in der EU, egal?
  - Gibt es Vorgaben, die ihr nachweisen müsst (BSI C5, ISO 27001, DSGVO, interne Richtlinien)?
  - Wohin soll das Geld gehen: möglichst niedrige Kosten, ausgewogen, oder Schutz zuerst
    (mehr Aufzeichnung, jede Stufe wie die Produktion)? An der Sicherheit selbst ändert das nichts.
```

```
Briefly describe what you need. Everything here helps, none of it is required:
  - What is it for? There is a development, a test and a production stage, unless you say
    otherwise (a sandbox only to try things out, one more stage)
  - Who works with it, and from where (only staff on the company network, partners, the internet)?
  - How bad would it be if it were unreachable for a day?
  - How far back do you need to get if someone deletes something by accident?
  - Must a copy survive if someone destroys the data on purpose (ransomware, a hijacked
    admin account)?
  - Where may the data be stored and processed: only in the country, only in the EU, anywhere?
  - Are there requirements you must prove (BSI C5, ISO 27001, GDPR, internal policies)?
  - Where should the money go: lowest running cost, balanced, or protection first (more
    records, every stage like production)? The security baseline is the same in all three.
```

Then map the answer onto the deployment set and every routed question set. Everything it
settles is recorded with `source: stated` and is not asked again. Three rules for the
mapping:

- **A value is stated only if the user said it.** "Internal only" ("Nur intern") settles
  `network_exposure: private`; it does not settle an address range. An inferred value that
  the text does not carry belongs to the normal resolution order, not to `stated`.
- **A contradiction is asked, not resolved.** "Publicly reachable" ("Öffentlich erreichbar") next to
  "company network only" ("nur aus dem Firmennetz") is one question in Phase 3, quoting both halves.
- **The description may add resources.** "…with logs to Log Analytics" ("…mit Logs nach Log Analytics") routes a second
  question set through [azure-resources](../azure-resources/SKILL.md) — the same request,
  one interview, one spec.
- **A default is not an assumption.** "Assume nothing that isn't stated" ("Nimm nichts an, was nicht dasteht") removes guesses,
  never defaults: the stack `[development, test, production]` stays, with a named stage
  joining it rather than replacing it, and so does every other default in the sets. What
  the instruction forbids is inventing a value no default exists for — a range, a
  subscription, a name.
- **A referenced platform part answers the landing zone.** A named hub network, shared
  subnet or central workspace means a platform exists, so `landing_zone` is `corp` (private)
  or `online` (public), recorded as `forced` by that reference — never `standalone`, and
  never an open item, because the references are the answer.
- **A stated value holds in every stage, and posture is one per system.** "Publicly
  reachable is fine" ("Öffentlich erreichbar ist okay") said about the development stage is said about the system: the
  exposure is `public` in every stage, the network `none` in every stage. A run never
  splits a posture decision (exposure, local auth, keys, DNS, landing zone) by stage; only
  the customer's explicit word for a named stage does, recorded as `overridden` there.
- **An empty list is not always an answer.** Storage role assignments with shared keys
  off: an empty default renders an account nobody can use, so it is an `open:` entry with
  its owner rather than a decided value - read the question's `why` before recording `[]`.
- **Context values are bare.** `context:` holds values (`environments: [...]`,
  `workload: payments`, a per-stage map), not `value:`/`source:` records; the provenance
  of a context value is the deployment set's, under `deployment:`.

What remains open goes into Phase 3's batches. The description does not replace them; it
shrinks them, and usually to the `required` questions nobody mentions unprompted.

## Phase 1 — Establish the layout

The target is known from Phase 0. The same reading of the repository that answered it
settles how the code is split, which the spec records under `composition.granularity`:

- An existing `modules/` directory → match what is there, per module and per file
- **Stages are part of the layout.** `context.environments` — `[development, test,
  production]` unless the user said otherwise — renders as one root and one parameter
  file per stage (`environments/<stage>.tfvars`, `main.<stage>.bicepparam`) with one
  state per stage (a backend key, never a workspace). A value marked `per_environment`
  in its question is a parameter whose value lives in the stage's file, never a literal
  in the template; a stage whose values nobody could give gets its file with placeholders
  (the all-zero GUID, `OPEN-<what>`) and an `open:` entry naming it; the pipeline refuses to
  deploy a file that still holds one. Only what `non_production_savings` relaxes differs between the
  stages; everything else is identical, which is what the stack is for. A value the
  customer stated holds in every stage unless they said which stage; the savings relax
  defaults and derived values only.
- An existing `infra-spec.yaml` → its `composition` is `carried`; do not re-decide it
- A flat repository, or a single resource → `single`
- Otherwise → `per-concern`

Deciding this before the interview matters because it is the one thing both backends must
agree on. If the split is settled per renderer, the same spec produces one Terraform root
and six Bicep files, and comparing the two outputs stops meaning anything. See
[references/spec.md](references/spec.md#modularity).

`deployment.module_source` is not read from the repository: it is asked first, in Phase 0,
and the repository only decides which answer is recommended (authored resource blocks
already there → `authored`). Under `avm` the split above is mostly decided too: one module
call per resource, the root holding the wiring, so `single` unless a pattern says
otherwise.

## Phase 2 — Resolve the deployment set, then every resource question

[`questions/deployment.yaml`](questions/deployment.yaml) is resolved **before** any
resource question set. It holds what is one decision per system rather than one per
resource, in two halves:

- **The context** — environment, region, workload, subscription, resource group. Only
  the environment is asked. Region, workload, subscription and resource group are
  `parameterized`: never asked, rendered as input variables, supplied at deploy time —
  a user who is only designing has no deployment target yet. Use them from the
  description if stated (as the variable's documentation/example, not a baked-in value).
  **A parameterized value is never an `open:` entry**: a parameter without a value is
  complete, and `open:` is for decisions nobody could make, not for inputs the stage file
  supplies. A stage whose parameters are unknown simply has no stage file yet.
  The environment is `required`, because nothing can be guessed and everything downstream reads them. A
  resource question marked `from_context: true` points here; without this group that field
  pointed at nothing, and a run could reach the renderer with no region and therefore no
  name.
- **The deployment decisions** — network exposure, local auth, who owns the virtual
  network and the workspace, mandates and what they force, DNS ownership, retention and
  the ingestion cap.

Resolve it once and every resource inherits it. A resource question carrying
`from_deployment: <id>` is answered from there and never asked again — eight resources in
one run must not produce eight separate exposure answers, and a system is not private
because seven of them are.

**Read every question set before Phase 3 asks anything.** That is the set of each resource
the request names **plus** every resource a deployment decision forces into the design: a
private network exposure brings the virtual network and its private-endpoint subnet, a
diagnostics or retention decision brings the Log Analytics workspace, a registry or
identity requirement brings its own resource. Work out the full resource list from the
deployment set first, then read all of the sets in one pass. A set read after the batch, or
after Phase 5 has begun, means its interview questions could not be asked and its defaults
are guesses.

For each question, the answer then comes from the first source that has one:

| # | Source | `source` recorded as |
|---|---|---|
| 1 | What the user said — the request and the Phase 0 description | `stated`, or `overridden` where it changes a carried value |
| 2 | The existing `infra-spec.yaml` | `carried` |
| 3 | The repository's `platform.yaml` | `platform` |
| 4 | A pattern skill's pre-answers | `pattern` |
| 5 | The deployment set's answer: copied for a `from_deployment` question, mapped through the question's table for a `derived_from` one | `deployment`, or `requirement` with `derived_from: deployment.<id>` |
| 6 | The question's `default` | `default` |

A carried value outranks a pattern and a default on purpose: it was decided, and quite
possibly deployed. A re-run that let a pattern or a changed guardrail flip it would turn
"add a key vault" into a silent change to the storage account. Only the user changes a
carried value. Consequences are the exception — `deployment` and `forced` values are
re-derived from what they follow, not carried.

A question with `required: true` has no default and no safe guess. It is the only kind you
must ask. A question with `resolved_by: interview`
([question-set-format](references/question-set-format.md#who-resolves-it-resolved_by)) is
put to the person; one with `resolved_by: platform`, or none, is never put to a customer —
it resolves from the profile or the default, and a
`required` one nobody present can answer becomes an `open:` entry naming its owner.

**A forced value is pre-answered, not asked.** `key_protection: hsm` requires a Premium Key
Vault; `network_exposure: private` requires the private-endpoint subnet. Apply the
consequence, record it with the question that forced it, and say so in Phase 4 rather than
putting a question whose answer is already determined to the user.

Defaults are not invented per resource — they come from
[references/guardrails.md](references/guardrails.md), which is also where their reasoning
lives. Read it before choosing any default or justifying one.

## Phase 3 — Ask, in one batch

Only what Phase 0's description left open reaches this phase, and only the questions the
mode allows. A question the user already answered in prose and is asked again tells them
the description was not read.

**Never asked in any mode, whatever the description leaves open: the workload short name,
the subscription id, the resource group and the region.** They are `parameterized` context
in the deployment set - input variables the stage file supplies, not decisions. A question
about them, "there is no default for these" included, is a bug in the interview: the person
is designing and has no deployment target yet. The group's *name* is that kind of value; the
`resource_groups` group of the deployment set is not: whether areas get a group of their own
(`resource_group_split`) and whether each group exists or is created
(`resource_group_mode_<role>`) are interview questions, with `existing` and no split as the
defaults. Nor is the customer's language:
it is the language the request and the answers are written in, and Phase 0 writes it to
`context.language` (`en` or `de`) - the picture, the decision document and the
customer-facing text in the spec follow it.

**There is one batch**: the surviving interview questions — the
environment, who reaches it and from where, the mandates, and the `requirements` group
(network requirements - may the network be chosen freely, or are ranges assigned or a
connection to the company network given -, outage impact, data-loss tolerance, access pattern, backup isolation, data
residency, priority - cost, balanced or protection first, which moves cost and hardening
knobs and never the security floor), fewer only where the description stated an answer. **The `requirements` group is asked in
full, every run**: a requirement that has a default is still asked, because the default
is the guardrail's guess and the customer is the only one who knows - skipping one because
the batch looks long is the failure this group exists to prevent. There is no cap on the
number of customer questions: the customer answers multiple choice, and a tenth option
row costs them less than a decision nobody asked them about. **The batch is
asked in topics, not as one list**: every interview question carries a `topic` (`platform`,
`network`, `security`, `resilience`, `data`, `application` - the headings and their order are in
[question-set-format.md](references/question-set-format.md#the-interviews-topics-topic)),
the questions of a topic stand together, the topics in that order, and a topic with no
surviving question is left out. The `AskUserQuestion` call is cut at the topic, not at a
count: it takes four questions per call, so a topic of up to four is one call whose `header`
is the topic's short name (*Rahmen*, *Netzwerk*, *Sicherheit*, *Ausfall*, *Daten*,
*Anwendung* / *Setup*, *Network*, *Security*, *Outage*, *Data*, *Application*; the header
chip holds twelve characters). A topic of more is several calls in a row, and then **every
header is numbered** - *Rahmen 1/3*, *Rahmen 2/3*, *Rahmen 3/3* - so the same word never
appears twice in a row without telling the person how far along they are; a topic of one call
carries no number; small neighbouring topics
share a call only when each of them is a single question. The first line of a call names the
topic and the person's place ("Netzwerk - Frage 1-2, danach Sicherheit, Daten"), with
nothing reasoned or reported between the calls - the batch is never trimmed to four to fit
one call. **No option in the batch is marked recommended**: an interview question asks for a fact about the organisation - whether the
system joins the company network, how bad a day's outage is, where the data may live - and
there is no better answer the plugin could know. The default is the guardrail's fallback for
an answer nobody gave, not advice, and marking it steers the person towards the guess the
question exists to replace. **The one exception is the address range when the network is
free** (`network_requirements: free`): the batch offers three ranges out of a private block
nobody peers with - 10.100.0.0/24, /23, /22 - with the size that fits the described system
marked recommended, because that recommendation is sizing the plugin derives from the
system (compute subnets, private endpoints, a Container Apps environment), not a guess
about the organisation; the rule and the sizes are on `address_space` in the deployment
set, and each stage takes its own block of the chosen size. Nothing else is asked. A question without `resolved_by` takes its default; a `platform`
question takes the profile's value or its default; a `required` question of either
kind that nothing answers becomes an `open:` entry with its owner named, and Phase 4
says so. Put the batch in the customer's words — the `ask` texts of the `requirements`
group are written for that — and never a decision's vocabulary (`ZRS`, `TLS1_2`, a
subnet) in a question to a customer.

Phase 1 asks nothing: the target was Phase 0's first question and the layout is read
from the repository. A round trip per phase is the serial interrogation this protocol
exists to avoid.

**One exchange, every question in it.** Where the host offers `AskUserQuestion`, use it —
grouped options with the trade-off in the description beat prose. The deployment set is
resolved before the resource sets (Phase 2), so an interview question a resource set
carries is already filtered by the deployment answers when it reaches the batch -
`network_exposure: private` has removed the firewall questions before anyone sees them.

A serial interrogation ("and now, the TLS version?") is the one failure mode that makes
people abandon a tool like this, and it is entirely avoidable: the question set is known up
front, so there is no reason to discover questions one at a time.

If a question without `resolved_by: interview` survives into the batch, something is wrong: it
is asking a thing that should have a default, a platform value or an `open:` entry. Never
ask it; default it and say so in Phase 4, or open it with its owner.

**Never invent a value nobody gave.** Grouped options work for an `enum`, where the
values come from the question set. A `ref`, an address range, a subscription id, a
workspace name — anything only the environment knows — is never offered as an option and
never guessed: it comes from `platform.yaml`, from the stage file, or from the person's
own prose in Phase 0, and otherwise it is an `open:` entry naming its owner. An
unassigned address range is a blocker to say out loud, not a gap to fill with
`10.0.0.0/16`; a workspace that does not exist yet is a boundary — something this run
does not create — and the honest answer is to record it as missing rather than to
reference a name nobody has.

**Ask in the user's language; keep the artefacts in English.** The question sets are
written in English, but a question put to someone who wrote their request in German is
translated — including the trade-off in the options, which is the part that earns the
question. What stays English regardless: `infra-spec.yaml`, its `why` entries, code
comments, variable names and commit messages. They are the interface other backends,
reviewers and tools read, and a spec that is half German is a spec nobody can diff. Where
the user wants the reasoning in their language too, that is their call to make — ask once
rather than deciding it for them.

A question may carry `confirm_in: [production]`. Its default still applies, but in that
environment you surface it for confirmation rather than applying it silently — these are
the values whose blast radius makes a silent default inappropriate. It is not a question
and nothing is asked in Phase 3: the row appears in Phase 4's security block and in the
decision document marked *bitte bestätigen* / *please confirm* where the spec has the stage
named, and the sign-off option *Ja, aber bei der Sicherheit weicht etwas ab* is how the
person changes it. A confirm row is never dropped to keep the block short.

## Phase 4 — Show the design, report what was defaulted, then ask once

**First the design, as a list the customer ticks off**. Before
the account of defaults and before any file is written, say in the customer's words what
will be built: one line per part with what it is for, one line per connection, the handful
of decisions that cost money or change what the system can do. Nothing technical, no
attribute names - the customer recognises their system or says what is missing, which is
cheaper here than after the picture and far cheaper than after the code:

```
Das würde ich bauen - bitte abhaken, was stimmt:
  [ ] Eine Chat-Anwendung als Container, aus dem Internet erreichbar, Anmeldung mit Firmenkonten
  [ ] Ein Sprachmodell und ein Embedding-Modell (AI Foundry), nur in der EU
  [ ] Ein Suchindex über eure Dokumente (AI Search)
  [ ] Ein Speicher für die Dokumente und ein Datenbank für die Chatverläufe
  [ ] Ein Tresor für das eine Geheimnis, das die App braucht
  [ ] Ein eigenes Netz, 10.100.0.0/24, in dem alles außer der App nur privat erreichbar ist
  [ ] Logs aller Teile an einem Ort, 30 Tage
  Verbindungen: die App spricht mit Modellen, Suche, Speicher, Datenbank und Tresor; die
  Suche liest den Speicher und die Modelle. Nichts anderes spricht miteinander.
  Was Geld kostet oder euch einschränkt: eine Stufe (Sandbox), keine zweite Region, keine
  getrennte Sicherungskopie - alles so, wie ihr es beantwortet habt.
```

```
This is what I would build - please tick what is right:
  [ ] A chat application as a container, reachable from the internet, sign-in with company accounts
  [ ] A language model and an embedding model (AI Foundry), EU only
  [ ] A search index over your documents (AI Search)
  [ ] A store for the documents and a database for the chat histories
  [ ] A vault for the one secret the app needs
  [ ] A network of its own, 10.100.0.0/24, in which everything except the app is private only
  [ ] Logs of all parts in one place, 30 days
  Connections: the app talks to models, search, storage, database and vault; search reads
  the storage and the models. Nothing else talks to anything else.
  What costs money or limits you: one stage (sandbox), no second region, no separate
  backup copy - all as you answered it.
```

It is a list, not a summary. No preamble that names a phase ("Phase 3 is complete, let me
summarise" / "Phase 3 ist abgeschlossen, ich fasse zusammen"), no paragraph that strings the parts together with commas: the person
reads one line per part and ticks it, that is the whole point of the shape. The words are
the customer's: "logs", not "logging pipeline" ("Logs", not "Protokollierung"); "a store
for the documents", not "storage account with blob container" ("Speicher für die Dokumente",
not "Storage Account mit Blob-Container").

Before the question comes the **security baseline**, as a block of its own and grouped by
what it protects, never as the one line it used to be: *Zugang* (keys and shared secrets
off, company accounts only, no public access), *Verschlüsselung* (TLS floor, encryption at
rest, infrastructure encryption), *Schutz vor Löschen* (soft delete, purge protection,
locks), *Identitäten* (which part has which identity, and that the rest has none) and
*Protokolle* (diagnostics, retention) / *Access*, *Encryption*, *Protection against deletion*,
*Identities*, *Logs*. Every row is a decision of the spec - `source: default` or `forced` in a
`security` or `identity` group - in the customer's words, and the block comes from the spec,
not from memory. Nothing in it is asked; it is shown so that nobody finds it in the code.

```
Sicherheit - nach den Vorgaben gesetzt:
  Zugang          Anmeldung nur mit Firmenkonten, keine Schlüssel, kein öffentlicher Zugang
  Verschlüsselung mindestens TLS 1.2, Daten im Ruhezustand verschlüsselt, doppelt beim Speicher
  Löschschutz     gelöschte Daten 7 Tage wiederherstellbar, Tresor gegen endgültiges Löschen geschützt
  Identitäten     Apps haben je eine eigene, Konten und Registry haben keine
  Protokolle      alle Teile schreiben in den zentralen Workspace, 30 Tage
```

```
Security - set by the baseline:
  Access          company accounts only, no keys, no public access
  Encryption      TLS 1.2 or higher, data encrypted at rest, twice for the storage
  Deletion        deleted data restorable for 7 days, vault protected against purging
  Identities      each app has its own, accounts and registry have none
  Logs            every part writes to the central workspace, 30 days
```

Close it with one `AskUserQuestion`: **Passt das Design?** / **Does the design fit?** - *Ja, so bauen* / *Yes, build it that way* (recommended
when nothing is open) / *Ja, aber bei der Sicherheit weicht etwas ab* / *Yes, but something in the security baseline differs* (the person names the rows; only those are
opened, each recorded `source: overridden` with the reason, and the baseline stays as shown
for the rest; a row the guardrails refuse to relax - anything security-shaped in a
non-production stage - is said so, not applied) / *Etwas fehlt oder ist zu viel* / *Something is missing or too much* (the person says what; the spec is
not written until the list is right). A part the customer strikes is removed, a part they
add goes through `azure-resources` like any other request, and the account below is
redone for the change.

**Then the account of what was decided for them.** Compact - not forty rows, group it. It
opens with what the person's answers decided, in their words and their language, and
keeps the technical rows for the engineer section below it:

```
Was aus euren Antworten folgt:
  Ausfall wäre störend        -> Daten liegen in drei Rechenzentren der Region (ZRS)
  Eine Woche zurück           -> gelöschte Dateien und Ordner 7 Tage wiederherstellbar, alte Versionen bleiben
  Daten in laufender Nutzung  -> Standard-Speicherklasse, kein Aufpreis beim Lesen
  Nur aus dem Firmennetz      -> kein öffentlicher Zugang, Anbindung über private Endpunkte

Nach den Vorgaben gesetzt (ohne Rückfrage):
  Zugriff nur mit Firmenkonten, verschlüsselt, Logs in den zentralen Workspace

Offen (braucht jemanden vom Plattform-Team):
  Welche Anwendung greift zu und braucht welche Rechte?
```

```
What follows from your answers:
  An outage would be disruptive -> data sits in three datacenters of the region (ZRS)
  One week back                 -> deleted files and folders recoverable for 7 days, old versions stay
  Data in active use            -> standard access tier, no surcharge for reads
  Company network only          -> no public access, connected through private endpoints

Set by the baseline (no question asked):
  Access only with company accounts, encrypted, logs to the central workspace

Open (needs someone from the platform team):
  Which application accesses it and needs which permissions?
```

The engineer's view follows, as before:

```
Deployment-wide:
  exposure        private - every resource gets a private endpoint, no public surface
  network         own vnet, 10.42.0.0/16
  mandates        BSI C5 -> HSM key protection -> Key Vault Premium
  diagnostics     log-we-prod-platform-01

Defaulted (guardrail baseline):
  Security        TLS 1.2 floor, shared-key auth off, infrastructure encryption on
  Data protection blob soft-delete 7d, container soft-delete 7d, versioning on
  Observability   diagnostics -> Log Analytics, categories: audit + allLogs

Per stage (one file each; development and test hold placeholders until the platform team answers):
  production      sub 1111…, rg-invoicing-prod-we, hub vnet-hub-prod-we, ZRS
  development     sub ?, rg ?, hub ? - LRS (non_production_savings)
  test            sub ?, rg ?, hub ? - LRS

Asked:
  stages          development, test, production (default; "Produktion" named the production stage)
  location        westeurope
```

The deployment block comes first because it is what the rest hangs off, and a forced value
is shown with what forced it — `HSM -> Premium` is a cost consequence someone may want to
argue with, and they can only do that if they see the chain.

This is the step that keeps the plugin honest. Someone who disagrees with a default needs
to see it to disagree with it, and the ones they never look at cost one glance.

## Phase 5 — Working mode, spec, diagram loop, then the code question

Phase 5 runs in this order, for a new spec and for the extension of an existing one alike:
**working mode, spec, diagram loop, code question.** Nothing before the working mode is
written or drawn, and nothing after the diagram loop is generated until the code question
has been answered with a yes.

**First, ask how the rest of the run works - once, as the first step of Phase 5, before
the spec is written.** With the Agent tool available, ask through `AskUserQuestion`:
**Subagents** (recommended) or **Same session**. The answer covers both loops that follow -
the diagram loop below and the code loop of [iac-rendering](../iac-rendering/SKILL.md)
after the yes - and it is a working mode, not a decision: it is not written to the spec.
Say what it costs: agents check each other and work in the background, but each starts cold
and spends its own tokens; the same session is cheaper and does the steps itself. Only a
host without the Agent tool is not asked and runs in the same session. **A change or
extension of an existing spec enters Phase 5 again** - this question (unless already
answered in the session), spec, decision document, diagram loop, code question - it is not
a shortcut past any of them.

```
Wie soll ich weiterarbeiten?
  1. Mit Subagenten (empfohlen) - Ein Agent zeichnet, ein zweiter prüft das Bild, bevor du
     es siehst; später rendert und testet je ein Agent den Code. Gründlicher, kostet mehr
  2. In dieser Sitzung - Ich mache alles selbst, nacheinander. Günstiger, keine zweite Prüfung
```

```
How should I continue?
  1. With subagents (recommended) - One agent draws, a second reviews the picture before you
     see it; later one agent each renders and tests the code. More thorough, costs more
  2. In this session - I do everything myself, one step after the other. Cheaper, no second review
```

**Then write the spec.** `infra-spec.yaml` goes into the user's repository — the IaC root,
or `infra/` — and is validated with `check_spec.py`. Its shape is
[references/spec.md](references/spec.md#shape), and that is the whole format: the plugin
ships no sample spec to copy, and the scripts are tools, not documentation — run
`check_spec.py`, `new_diagram.py` and `export_decisions.py`, never read their source to
learn what a spec looks like. What `check_spec.py` rejects, it names.

**For a Terraform target, write `naming.yaml` beside it in the same step**, when the
directory has none: a full copy of
[naming.default.yaml](../iac-rendering/references/naming.default.yaml), with any departure
the user stated applied to it. The provider reads it at plan time, so it belongs to the
spec, not to the code — the names in the diagram and every later render come from it, and
a run that stops after the spec (the user says "not yet" / "noch nicht") must still leave the
convention in the repository. An existing `naming.yaml` is left untouched.

**For a Bicep target, write none** — nothing in a Bicep deployment reads it; the names are
`var`s generated into the template from the plugin's convention. Only a stated departure
(`naming_convention: custom`) is written, as a `naming.yaml` holding the departures alone.
The rules are in [naming.md](../iac-rendering/references/naming.md#namingyaml-in-the-users-repository--terraform-only).

**Record who reaches what in `wiring:`** when the spec holds more than one resource, from
what the request says — the diagram draws exactly this and nothing else
([spec.md](references/spec.md)). `wiring.access` is one `{ from, to, label }` per call the
request names ("the web app reads from the storage" / "die Web-App liest aus dem Storage" is `app-service` → `storage-account`),
with `users`, `internet` and `external:<name>` as the actors outside the deployment;
`wiring.purposes` is a few words per resource in the user's own terms ("Produktbilder");
`wiring.optional` lists what the user called optional. Never infer a call from the
resource types: two resources side by side say nothing about who talks to whom, and an
invented line in a picture the customer signs off on is a decision nobody made. A call
the request leaves out is an `open:` entry only where the spec cannot work without it;
otherwise the line is simply absent.

**Customer-facing text in the spec is written in the customer's language**, the one
`context.language` names - the one exception to the English spec: `wiring.access[].label`, `wiring.purposes` and the
`owner` of every `open:` entry are printed verbatim into the picture, the `question` into
the decision document (the picture counts the open entries by owner and points at the
document), so an English label there is a `spec` finding of the review. Keys, values, `why`, `reason` stay English.

**Write the decision document in the same step**, in the user's language:

```sh
python3 <plugin>/core/iac-authoring/scripts/export_decisions.py ./infra-spec.yaml
```

It renders every decision in the spec as one line in the customer's words
(`infra-decisions.md` beside the spec): what follows from their answers, with the
decisions derived from each; what the rules set; what they decided differently; what is
still open and from whom. It is the Phase 4 account as a file someone can send, and it is
regenerated from the spec on every later run like the diagram. It is the
artefact the person signs off on; the spec is for the engineer. The script reads the
question sets' `plain` lines and falls back to English where a line lacks the language,
and says how many did — translate those in the conversation rather than editing the file.

**Then run the diagram loop, without asking.** Nobody reads the spec; the customer reads the picture.
Run [iac-diagram](../iac-diagram/SKILL.md) on the spec as soon as it validates and put
`infra-diagram.drawio.png` beside it - every run, for a single storage account as much as
for twelve resources, because the picture is the thing the person signs off on and the
question "should I draw a diagram?" was a question nobody ever answered with no. Where the PNG cannot be exported (no draw.io CLI), hand over the
`.drawio` and say so.

**Review it before anyone sees it - Loop 1 of
[agents.md](../iac-rendering/references/agents.md).** The picture is not shown to the
customer as it comes out of the script. A **review agent** (read-only; with Subagents a
subagent, in the same session the session itself, with the same checklist) looks at the
PNG, works through [the checklist](../iac-diagram/SKILL.md#the-review-checklist) edge by
edge and reports a numbered list: a line through an icon or another line, overlapping or
wrapped labels, a label in the wrong language, a legend that contradicts a colour, a
number or a name that disagrees with the spec. **With Subagents the main session starts the
review agent itself, as its own Agent call after the draft exists** - with Subagents the
**main session runs the script itself** (`new_diagram.py`, `verify_diagram.py`,
`export_diagram.py --keep`: deterministic, seconds, nothing an agent that starts cold would do
better), then starts the review agent, then - only when the review found an `error` with cause
`render` - the **fix agent**. A subagent cannot start another, so a brief that tells one to "use a review
subagent" gets no independent review, and whoever edited the picture must never be the one that
checks. The review never shares an agent with the draft or the fix. Each finding carries a severity (`error`:
wrong, misleading or unreadable; `polish`: only looks worse than it could) and a cause
(`render`: the drawing; `spec`: the spec says it that way). An `error` with cause
`render` goes to the **fix agent**, which fixes it **by hand in the `.drawio`**
the way [iac-diagram](../iac-diagram/SKILL.md) says - the affected cells by id, a
waypoint, a geometry, a label - verifies, exports, and the review runs again. The script
is not touched in the loop: `new_diagram.py` exists to produce the first draft cheaply,
and the picture the customer signs off on is finished by hand. A fault the script would
repeat on the next spec is noted in the hand-over as a plugin todo, not fixed now. Three passes, then the customer
sees the picture as it is, with the open findings named. `polish` findings never go back;
they go into the hand-over. **The review has a ceiling**, because a reviewer always finds
more: at most **8 findings per pass, errors first**; the same
fault on several cells is one finding that lists the cells; it reads the PNG and the spec
and opens the `.drawio` only for a coordinate it needs, never samples pixels, and stops
once the list is full. A later pass reports only what the earlier passes named and what the
fix broke - never a fresh sweep. An `error` with cause `spec` is the main agent's: correct the
spec, re-export the decision document, regenerate the draft - **and do that before the
fix agent starts its hand edits**, because a regenerated draft loses them; the order
of a pass is spec findings first (the main session corrects the spec and runs the script
again), then the hand edits on the fresh draft, then the review again. Every finding names the cells it concerns by their draw.io ids (`e-6`,
`res-key-vault`), so the fix agent can act on it without re-deriving it. **Never show
the customer a picture with an error you have already seen** - that is what the loop is
for.

**The code question.** Every reviewed diagram ends in this question, in the same message
that shows it - after the first draw, after every redraw in the loop, after a diagram-only
request, after an extension of the spec. It is always asked: nothing the person said
earlier - "then write the code" / "dann schreib den Code", a stated target, an answer in the interview, a request
for a commit - stands in for it, and a run never skips it because the answer seems
obvious. A diagram shown without the question, or a
turn that ends on "diagram is done" or on a list of findings, is a missed step. It is asked with
`AskUserQuestion` - the interactive popup with the three options, as the call right after
the picture - and never replaced by prose like "let me know when I should render" or by
the question written out as text; the three options are the `AskUserQuestion` options.
Show the reviewed picture and the decision document's first section (what
follows from their answers), name what is still `open:` and from whom, and ask one
question. The German and English blocks below are the wording; it is asked in
`context.language`. The three options keep their meaning in any language: only the yes
starts the render.

```
So sieht das System aus (infra/infra-diagram.drawio.png); was ihr entschieden habt, steht
lesbar in infra/infra-decisions.md. Passt das so zu euren Anforderungen?
  - Ja, passt                 -> the picture is signed off; the code is generated next
  - Etwas ändern              -> the user says what; change the spec, redraw, ask again
  - Noch nicht                -> stop here; the spec and the picture stay, the next run extends them
```

```
This is what the system looks like (infra/infra-diagram.drawio.png); what you decided is
in infra/infra-decisions.md in readable form. Does this fit your requirements?
  - Yes, build it             -> the picture is signed off; the code is generated next
  - Change something         -> the user says what; change the spec, redraw, ask again
  - Not yet                   -> stop here; the spec and the picture stay, the next run extends them
```

"Change something" ("Etwas ändern") loops back to the spec, never into code: change the decision there, as
`overridden` where it replaces an answer, re-export the decision document, redraw, review
again, ask again. An objection to the picture itself ("the arrows overlap" / "die Pfeile überlappen sich") is a
review finding that the review missed: it goes to the fix agent like any other
`error`, and the customer sees the picture again only after the review passed. Stay in this loop as long as the person has objections - a round costs seconds
here and a regenerated module later. Offer the decision document as Word once, in the
first round, as a side line and not an option: the `.docx` is a conversion
(`pandoc infra-decisions.md -o infra-decisions.docx` where pandoc is on PATH; say so and
leave the Markdown where it is not).

**Only after "Yes, build it" ("Ja, passt") does the render start** ([iac-rendering](../iac-rendering/SKILL.md)),
into the same directory, with its own loop of fmt, validate, tests and plan - Loop 2, in
the working mode chosen above. It is the
long step, and it runs on a picture the customer has agreed to, so nothing in it goes
back to the interview. Say that it takes a while and what will be there at the end.

**An earlier statement is not the answer.** "Dann schreibe den Terraform-Code" in the same
message as the spec, or a change of the spec the person asked for themselves, still goes
working mode, spec, diagram, review, question - the code is what they sign off on, not
what they ordered, and the question is put after the picture, never before it.
A run in which nobody can answer (no `AskUserQuestion`) ends after the diagram with the
sign-off question as the last message and writes no `.tf` or `.bicep`: a sign-off nobody
gave is not one, and the code would be built on a picture nobody has seen.

Never present the render as already decided. If the spec still holds `open:` entries or
`assumed` values, say so with the question — the code will then `plan` but not `apply` —
rather than letting "Ja, passt" read as "ready to deploy".

A spec extended by a later run goes through the same loop; the diagram and the code are
regenerated from the whole spec, so the diff shows what the extension moved.

- Spec schema and the `source` field: [references/spec.md](references/spec.md)
- Drawing it: [iac-diagram](../iac-diagram/SKILL.md)
- Rendering it, for either target: [iac-rendering](../iac-rendering/SKILL.md)

## Phase 6 — Validate and explain

Generated code is not done when it is syntactically valid: `fmt` → `validate` →
`plan` / `what-if` → explain what will actually happen and what is risky about it. The
commands per target are at the end of each idiom file in
[iac-rendering](../iac-rendering/SKILL.md).

Do not skip the explanation on the grounds that the plan output is right there. A plan is a
list of attribute diffs; what a reviewer needs is which of those diffs are
service-affecting and which are noise, and that is a judgement the plan cannot make.

## Composition: how a pattern drives a resource

A pattern skill does not re-ask a resource's questions. It supplies a pre-answer block
keyed by resource, entering resolution at precedence 2:

```yaml
pre_answers:
  storage-account:
    public_network_access: disabled
    shared_access_key_enabled: false
    replication: ZRS
  key-vault:
    rbac_authorization: true
```

Two rules make this work:

- **A pattern may pre-answer, never contradict the user.** If the user asked for something
  the pattern pre-answers differently, the user wins — and you say what the pattern
  expected and what the departure implies for the rest of the system.
- **The wiring belongs to the pattern.** Private endpoints, DNS zone links, role
  assignments between the parts, diagnostic routing: no single resource question set can own a
  relationship, so the pattern renders it. This is the genuinely hard part and the main
  reason pattern skills exist.

A pattern may also fix the module split, since it is the only layer that knows which parts
get reused separately. It does that by supplying `composition.modules` entries, recorded
with `source: pattern` like any other pre-answer:

```yaml
composition:
  granularity: per-resource
  modules:
    - id: storage
      contains: [storage-account]
      outputs: [id, principal_id]
    - id: app
      contains: [app-service]
      needs: [storage]
```

The wiring between them stays in `wiring:` and renders into the root, not into a module —
a module that reaches into another module's resources is the failure this split exists to
prevent.

## Adding a resource

A resource goes into a family under `resources/` — `storage`, `network`, `observability`
today, `compute`, `data`, `security` planned. Families are not skills; the single
[azure-resources](../azure-resources/SKILL.md) skill routes into all of them. Inside the
family:

1. Create `<resource>/` in the family and write `<resource>/questions.yaml`. Copy an existing one and keep the group order:
   placement, networking, identity, security, data_protection, observability. The order is
   the review order, and a reviewer reading three resources should not relearn the layout.
2. Fill `why` and `renders` for every question. `why` is what a reviewer reads; `renders`
   names the attribute it drives, which is what lets a review map code back to a decision.
3. Take defaults from [references/guardrails.md](references/guardrails.md) rather than from the
   Azure portal. They differ often, and the portal default is not a baseline worth
   inheriting.
4. Mark `required: true` only where no safe default exists. Every extra required question
   is a tax on every future run.
5. Write `<resource>/notes.md` for what the question set cannot express:
   decisions fixed at creation, dependency order, the pitfalls worth naming out loud.
6. Write `<resource>/terraform.md` and `<resource>/bicep.md` — the
   rendering, not the decisions. Anything true for both belongs in the shared references
   instead.
7. Add a row to the family's `routing.md`, so the resource is reachable, and its icon to the
   `ICONS` table of [iac-diagram](../iac-diagram/SKILL.md#icons), so it is drawable.
8. If people would ask for it with a term the
   [azure-resources](../azure-resources/SKILL.md) description does not carry, add the term
   there, never here — resource terms are its job, workload and target terms are this
   description's, and this one stays short so the entry is never what gets pruned.
9. Validate with `scripts/check_question_set.py <resource-directory>` — enum defaults,
   `depends_on` and `from_deployment` targets, the resolution fields, unknown fields —
   and with the repo's `check_repo_consistency.py` for routing reachability.

A genuinely new family gets a directory under `resources/` with a `routing.md`, and a row in
the azure-resources table. **Not** a skill directory and **not** a `plugin.json` entry:
`resources/` is deliberately undeclared, so nothing in it costs listing budget, and a
family that became a skill again would reintroduce the per-family budget cost that
overflowed at the sixth family.

## Reference files

Read as needed, not up front:

| File | When |
|---|---|
| [references/spec.md](references/spec.md) | Writing or reading `infra-spec.yaml` |
| [references/question-set-format.md](references/question-set-format.md) | Authoring or extending a `questions.yaml` |
| [references/guardrails.md](references/guardrails.md) | Choosing or justifying any default, or weighing an exception |
| `scripts/export_decisions.py` | Rendering the spec as `infra-decisions.md`, the customer's decision document |
| [iac-diagram](../iac-diagram/SKILL.md) | Drawing the spec as `infra-diagram.drawio.png` for the customer |
| [iac-rendering](../iac-rendering/SKILL.md) | Turning the spec into Terraform or Bicep — naming, layout, idiom |
