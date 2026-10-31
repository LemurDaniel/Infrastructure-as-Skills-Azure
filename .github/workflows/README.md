# Workflows

File names are `<kind>.<topic>[.<variant>].yaml`. The exception is the eval agent's
infrastructure pair: `iac-rendering` renders it from `eval-agent/infra/infra-spec.yaml`
under the names its pipeline reference sets (`<root>-infra.yaml`), and it changes through
the spec and a render, never by hand (CLAUDE.md). `check_pipeline.py` checks it.

| File | Runs on | Content |
| --- | --- | --- |
| `check.pull-request.yaml` | PR into `dev` or `master` | Repository checks; into `master` also: from `dev`, version raised. Its job names are the required status checks |
| `deploy.eval-agent.dashboard.yaml` | push to `dev`, PR | Tests the dashboard, pushes its image through a short registry window and sets it on the web app |
| `eval-agent-infra.yaml` | push to `dev`, PR | Rendered entry: Bicep build and lint, then the `production` stage |
| `eval-agent-infra-stage.yaml` | called | Rendered stage: what-if, approval, deploy |
| `eval.plugin.yaml` | by hand | The plugin eval suite, recorded on `eval-history` |
| `refresh.foundry-models.yaml` | monthly, by hand | Regenerates the Foundry model catalogue, PR into `dev` |
| `release.plugin.yaml` | push to `master` | Tag, GitHub release and ZIP of the version in `plugin.json` |

The scripts the hand-written workflows call are in [`../scripts/`](../scripts/README.md).
