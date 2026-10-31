# Workflow scripts

The steps of the workflows in [`../workflows/`](../workflows/README.md) that outgrew an
inline `run:`. Python 3.9+ like every script of the repository, so nothing needs PowerShell;
the workflows call them from their pwsh steps. Each runs locally as well.

| File | Called by | Content |
| --- | --- | --- |
| `check_release_eval_run.py` | `release.plugin.yaml` | Warns when the release has no Sonnet run on `eval-history` or the badge names another version |
| `run_eval_suite.py` | `eval.plugin.yaml` | Runs the eval cases one by one under a cost ceiling, merges the results |
| `run_repository_checks.py` | `check.pull-request.yaml`, `release.plugin.yaml` | The repository checks of a PR and a release |
| `update_foundry_models.py` | `refresh.foundry-models.yaml` | Writes `models.yaml` from the catalogue JSON of each region |
