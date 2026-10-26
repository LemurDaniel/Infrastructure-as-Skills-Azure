# Azure AI resources

A resource family, reached from the [azure-resources](../../core/azure-resources/SKILL.md)
skill. Routing table - the request picks the question set:

| Request mentions | Question set | Notes |
|---|---|---|
| AI Foundry, Azure OpenAI, OpenAI, model deployment, GPT, embedding model, AI Services | `foundry/questions.yaml` | [notes](foundry/notes.md) |
| AI Search, Azure Search, Cognitive Search, vector search, search index | `search-service/questions.yaml` | [notes](search-service/notes.md) |
| Speech, Speech Services, Computer Vision, OCR, Language service, Text Analytics, Document Intelligence, Form Recognizer, Content Safety, Translator, Custom Vision, Face API (one service, standalone) | `ai-services/questions.yaml` | [notes](ai-services/notes.md) - one account per service, same resource provider as Foundry; several services on one account is the foundry set |
| Azure Machine Learning, ML workspace, AML, Machine-Learning-Arbeitsbereich, training jobs, managed online endpoint, MLOps | `machine-learning-workspace/questions.yaml` | [notes](machine-learning-workspace/notes.md) - kind Default with referenced storage, vault, insights and registry; the Foundry hub/project kinds are the foundry set |
| Azure Bot, Bot Service, Bot Framework, Teams bot, Direct Line, Web Chat, Chatbot-Registrierung | `bot-service/questions.yaml` | [notes](bot-service/notes.md) - the registration and channels in front of a bot application hosted elsewhere; Bicep is authored (module Proposed) |
| agent, prompt flow, evaluation | *not written - application content* | Not infrastructure |

When a question set does not exist yet, say so rather than improvising one. Fall back to
[the guardrails](../../core/iac-authoring/references/guardrails.md), generate from those
rules, and record in the spec that no question set backed it.

## Then

1. [iac-authoring](../../core/iac-authoring/SKILL.md) - the interview protocol, and
   [the deployment set](../../core/iac-authoring/questions/deployment.yaml), which already
   answers exposure, `local_auth` and `key_management` before this set runs
2. [iac-rendering](../../core/iac-rendering/SKILL.md) - the spec into Terraform or Bicep

## True for the whole family

**These resources are called, not hosted on.** Almost every decision is inherited (exposure,
keys off, diagnostics) or derived from `outage_impact`; what the family adds is what is not
guessable - which model, how big a search service - and those are the engineer's, becoming
`open:` entries when nobody can answer. A customer is asked nothing new.

**Keyless means every caller has a role, and the roles are the narrow ones.** An application
calling a model, a search service and a data store holds a role on each; with keys off an
empty role list is a working resource nobody can use. A pattern grants them from the
consumers it knows.

**The connections between the resources are the pattern's.** A Foundry project reaching a
search service, a search indexer reaching a storage account over a shared private link, a
model called from a skillset: each is a role on one side and often a private link on the
other, and neither set owns it.

**What is fixed at creation is the decision to take slowly.** A search service's tier, an
account's kind and subdomain, a deployment's model: each is rebuilt, not edited, and each
question set says which in its `why`.

**Quota and regional availability are outside the template.** A model, a version or a tier
that the region does not offer fails at apply, and the fix is a different region or a quota
request - check before the interview ends.
