# Eval agent

**Status:** the agent half is superseded (2026-10-27). The evals run in GitHub Actions
(`.github/workflows/eval.plugin.yaml`, by hand; the full suite on Sonnet before a merge), each
run is recorded on the `eval-history` branch, and the dashboard only shows that history per
plugin version and model - no run start, no tickets, no GitHub token. `app-service__agent` and
its identity are out of the spec and the render. Why: an always-on App Service and a private
endpoint for a job that runs a few times a week, in a test subscription, cost more than the
runs. What follows is
the original sketch.

## Idea

Two parts that together close the loop after an eval run. Today a run ends in a terminal:
someone reads `show_eval_result.py`, decides what is a regression, writes the `LEARNINGS.md`
entry by hand. The parts do the reading and the paperwork; the owner decides what to fix.

- **Agent** - runs the eval suite on request and writes the results to storage. Runs plugin
  code, so it holds no secret and is not reachable from outside.
- **Dashboard** - shows the runs over time and, after a run with failed evals, files the
  tickets (GitHub issues) in this repository. It is the internet-facing part (sign-in with
  company accounts), so it only reads the results and holds one narrow token.

## Flow

1. **On request** - the dashboard starts a run through the agent's private endpoint, with a
   scope: all cases, one group, or one case. Says what the run costs before it starts.
2. The agent runs `claude plugin eval` and `show_eval_result.py`, compares with
   `baseline.json` and writes the result files to storage.
3. The dashboard **triages** by the method in `plugin-evals` section 5: harness errors first
   (no ticket for the plugin), then REGRESS, then UNSTABLE, then plain failures; grouped by
   probable cause.
4. The dashboard **files tickets** - one per cause, not one per failing grader: case, grader,
   pass rate vs. baseline, the failing spec excerpt, the suspected skill or question set, a
   proposed `LEARNINGS.md` entry. Looks for an open ticket on the same grader first and
   comments instead of duplicating.
5. Never touches `baseline.json`, a case or a skill. Accepting a run stays a human step.

## Why

Evals are only worth what is done with their results. The reading is mechanical enough to
hand over, the judgement (is the grader wrong or the plugin?) is not - so the ticket carries
both hypotheses and leaves the call open.

## Why two apps

The two parts need opposite things. The agent executes plugin code and fetches its source
from outside: it needs the models and the right to write results, and must see no secret.
The dashboard is reachable from the internet: it needs the sign-in secret and the ticket
token, and must not be able to call the models or write results. One app with one identity
gives both of them all of it, so a compromised agent would hold the token and the sign-in
secret.

- Two App Services on one plan, each with its own user-assigned identity.
- Agent: private endpoint only, roles AcrPull, Storage Blob Data Contributor, Azure AI User.
- Dashboard: public with Entra sign-in, roles AcrPull, Storage Blob Data Reader, Key Vault
  Secrets User; the token is `issues:write` on this repository only.
- The tests assert the separation: no vault role for the agent, no model role and no write
  role for the dashboard.

## Related

- [Diagram fuzz](diagram-fuzz.md): a second job type of the agent - Python only, no model call,
  results into the same storage.

- [Autonomous Terraform agent](autonomous-terraform-agent.md) and
  [AVM drift watch](avm-drift-watch.md): same agent host, same ticket/PR mechanics.
- [Eval dashboard](eval-dashboard.md): the dashboard of this idea; the ticket and the
  dashboard read the same result files.

## Open questions

- ~~When does the dashboard file a ticket~~ Decided 2026-10-25: on a click, no trigger in
  the dashboard. Automatic filing stays an option once the noise threshold below is set.
- Who puts the GitHub token into the vault (`github-token`), and who creates the client
  secret of the sign-in (`entra-client-secret`)?
- Ticket noise: a threshold before a flaky grader becomes a ticket (UNSTABLE in two
  consecutive runs?).
- Cost: a full run is about $5; a cost ceiling per request, and a cheap mode (one run per
  case, no baseline arm) as the default.
- Close tickets automatically when the grader is back at its baseline rate, or only comment?
- Linux hosting brings back the shell-based graders on a runner the agent image has to
  provide.
