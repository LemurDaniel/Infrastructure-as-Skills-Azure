# Workflow scripts

The steps of the workflows in [`../workflows/`](../workflows/README.md) that outgrew an
inline `run:`. Each runs locally from the repository root as well.

| File | Called by | Content |
| --- | --- | --- |
| `Invoke-PluginEvalSuite.ps1` | `eval.plugin.yaml` | Runs the eval cases one by one under a cost ceiling, merges the results |
| `Invoke-RepositoryChecks.ps1` | `check.pull-request.yaml`, `release.plugin.yaml` | The repository checks of a PR and a release (`-Python python` on Windows) |
| `Test-ReleaseEvalRun.ps1` | `release.plugin.yaml` | Warns when the release has no Sonnet run on `eval-history` or the badge names another version |
| `update_foundry_models.py` | `refresh.foundry-models.yaml` | Writes `models.yaml` from the catalogue JSON of each region |
