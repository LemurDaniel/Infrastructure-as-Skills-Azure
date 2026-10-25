# Diagram fuzz

**Status:** sketch; the fuzzer exists as `tools/diagram-fuzz/run_fuzz.py` (outside the plugin: development tooling, not shipped), the hosting is not built

## Idea

Random valid specs are drawn with `new_diagram.py`, checked with `verify_diagram.py` and scored
on the geometry of the `.drawio` (edge crossings, edges through foreign icons, label overflow,
aspect ratio). The worst cases show where the layout code is weak; each one becomes a fixture
and a fix. Aesthetics, not correctness: a hard failure (crash, verify mismatch, overlapping
icons) is a bug, everything else is a ranking.

## Where it runs

- **CI first** - a job in this repo: `run_fuzz.py --n 100 --seed <run number>`, the worst five
  as a workflow artifact, a soft gate on the mean score.
- **On the [eval agent](eval-agent.md)** - a second job type next to `claude plugin eval`, no
  new infrastructure. It needs Python and PyYAML only: no model call, no secret, no draw.io, so
  the agent's identity (no vault role, no model role) is more than enough. It writes
  `report.json` and the worst specs into the results storage the agent already writes to;
  the [dashboard](eval-dashboard.md) reads the score over time next to the eval runs.

## Fuzzer and tuner on a branch of their own

The tuner improves `new_diagram.py` on a branch (`tune/layout`), not through pull requests: a
second fuzz run on the state of an open pull request measures the same thing again. On its
timer the tuner asks the fuzz agent whether a run is going and does nothing if so; otherwise it
drafts a change, re-runs the fuzzer and the tests, commits to the branch only when the score
drops and the tests pass, starts the fuzz agent and waits for its next timer. The fuzz agent has
no schedule of its own. The owner merges the branch when they like.

- The tuner changes `new_diagram.py` and adds fixtures; never the fuzzer, its metrics, an
  existing test or `master` (a branch rule keeps its token off `master`).
- The score measures crossings and overlaps, not whether a picture is good: new seeds each run
  next to a fixed comparison set, a limit of commits per day, and the pull request to `master`
  shows the worst cases before and after.

## Why on the agent

It is plugin code run on a schedule with results into storage, which is the agent's job. A
third app would repeat the plan, identity and private endpoint for a script that runs seconds.

## Open questions

- The edge model is a straight-line proxy for draw.io's orthogonal routing. Is it good enough
  to rank, or does the score need the real routes (export through draw.io, needs the CLI in the
  agent image)?
- A threshold for the gate: the mean score moves with the generator, so the baseline is per
  generator version, like `baseline.json` of the evals.
- Should the dashboard file a ticket for a new worst case, or only show it?
- An unwired edge kind (`front-door`) is not drawn at all and `verify_diagram.py` fails; the
  fuzzer wires them. Intended?
