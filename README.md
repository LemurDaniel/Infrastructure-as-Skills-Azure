# eval-history

Data branch, no code. One entry per eval run in `index.json` (plugin version, model, trigger, pass rate per case), the full result under `runs/<version>/<id>-<model>/`. Written by `.github/workflows/plugin-evals.yml` through `record_eval_history.py`; read by the eval dashboard. The first entry is seeded from `evals/baseline.json` (v0.0.2 on Opus).
