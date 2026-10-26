# Single-service AI accounts - what the question set cannot express

## Fixed at creation

- **The kind** and the **custom subdomain**. The subdomain is the account's hostname, must be
  globally unique, and is required for token authentication, a firewall and private endpoints;
  neither can be changed.
- **The name.** Part of the subdomain and the endpoint.
- **The region.** It decides which kinds and features exist and where some of them process.

## Ordering

The identity and its role on the Key Vault key (when `key_management: customer_managed`), the
storage account the kind trains from or writes to (with the account identity's role on it - a
pattern's wiring), then the account, then the role assignments of the callers, then the
workspace's diagnostic setting. `Face` and the gated Speech features need the subscription's
use-case registration approved before the account can be created at all; without it the apply
fails with an eligibility error that no template fixes.

## Pitfalls

**Several services are one resource type, and the set is one of two.** A request that names
Speech *and* Language *and* OpenAI is the multi-service `AIServices` account of the foundry set,
with one endpoint and one key space; a request for one service is this set and an account per
service. Two single-service accounts cost nothing extra and keep roles, quotas and diagnostics
apart; the multi-service account is for an application that calls several and wants one
endpoint.

**The kinds kept their old names.** `TextAnalytics` is the Language service, `FormRecognizer` is
Document Intelligence, `SpeechServices` is Speech; the portal names differ from the ARM kinds,
and the role names differ from both. The set's `plain_values` carry the portal names.

**Private endpoint plus the Speech SDK is a configuration, not a default.** Behind a private
endpoint the Speech SDK must be built with the account's private hostname
(`https://<subdomain>.cognitiveservices.azure.com/`), not the region shortcut; the application
setting is named in the handover. Batch transcription and synthesis callbacks also need the
storage account reachable from the service.

**Outbound restriction is the data-exfiltration control for URL inputs.** Vision, Document
Intelligence and Speech fetch what a caller's URL points at; with `restrict_outbound: true` and
an empty `allowed_fqdns` the account reads only request bodies. The first failing call usually
names the missing host.

**Free tier is one per subscription and kind.** `F0` fails the second stage in the same
subscription, is throttled and refuses some features; it is a deliberate choice for one
engineer, never a stage default.

**Some features process outside the region.** Speech translation and some Translator features
route through other regions of the geography; a `data_residency: country` customer is told
which features, read from the service's data-residency page before the interview ends.

**Customer-managed keys are not uniform across kinds.** Some kinds take them on `S0`, some need
`E0`, some do not support them at all; check per kind before a render and record a forced
`platform_managed` with the kind as the reason where unsupported.

**The modules disagree on defaults.** Local authentication (Terraform on, Bicep off), outbound
restriction (Terraform off, Bicep on) and public access differ; every decision is written on
the call.

**Log category names are the platform's** and differ per kind: checked against
`az monitor diagnostic-settings categories list --resource <account id>` before a render.

## Not covered here, and why

Multi-service accounts, model deployments and projects (foundry set), custom models and their
training data, commitment tiers and disconnected containers, Bing search resources, the
retired kinds (LUIS, QnA Maker, Content Moderator, Anomaly Detector, Personalizer, Metrics
Advisor) and Video Indexer have no question set; a request for one is said out loud, not
improvised.
