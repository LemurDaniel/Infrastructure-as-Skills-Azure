# Rendering with agents

A render is four deliverables from one spec: the code with its tests, the pipeline, the
diagram, and the checks that tie them to the spec. They share one input and little else, so
they can run as agents. This file is the protocol; the order of work in
[SKILL.md](../SKILL.md) stays the contract each agent follows.

**When.** Ask when the Agent tool is available and the spec has several resource families:
one `AskUserQuestion` before rendering, with two options - **Subagents (recommended)** and
**Same session** - and run what the user picks. Say in the option text what it costs: agents
run in parallel and check each other, but each starts cold and uses its own tokens; the same
session is cheaper and sequential. A small spec (one resource, one family) is not asked: it
is faster done in sequence, because every agent reads the spec, the references and the
guardrails again. Without the Agent tool, do the same steps in the same order yourself.

## Two arms from one spec

```
                         ┌─ Arm A: Code ────────────────────────────────────────────┐
                         │  code agent ─> pipeline agent ─> test agent ─> green?    │
 infra-spec.yaml ─ main ─┤                    ^                              │ no   │
                         │                    └──────── findings ────────────┘      │
                         ├─ Arm B: Diagram ─────────────────────────────────────────┤
                         │  diagram agent ─> review agent ─> errors?                │
                         │        ^                              │ yes              │
                         │        └──────────── findings ────────┘                  │
                         └──────────────────────────────────────────────────────────┘
```

The arms run in parallel and never read each other's output. The main agent starts both,
counts the passes, routes findings and writes the hand-over.

| Agent | Does | May write | Never |
|---|---|---|---|
| **Code** | Steps 1-7 of the order of work: AVM resolution, names, code, tests per decision | The render root only | Pipeline, diagram, `apply`, a commit |
| **Pipeline** | Step 10, after the code agent has reported the layout (root, stage files, backend keys, working directory) | The pipeline files only | Code, tests |
| **Test** | `fmt`, `validate`, `test`, `check_render_coverage.py`, `check_pipeline.py`, the diagram's `verify_diagram.py` | Nothing | Fixing what it finds |
| **Diagram** | Step 9: `iac-diagram` from the spec | `infra-diagram.drawio.png` beside the spec | Code, pipeline |
| **Review** | Reads the PNG and compares it with the spec | Nothing | Fixing what it finds |

The test and review agents are read-only on purpose. The one that checks must not be the one
that edits: two authors on one file overwrite each other, and a checker that fixes its own
findings stops reporting them.

## Findings

A test or review agent reports a numbered list. Each entry has a location, what is wrong,
a **severity** and a **cause**:

- **Severity.** `error`: wrong, misleading or unreadable. `polish`: only looks worse than it
  could.
- **Cause.** `render` (the code, pipeline or drawing is wrong for this spec), `spec` (the
  spec says it that way: English text in a German diagram, a decision that is wrong at its
  source), `other`.

The main agent routes by cause. A `render` finding goes back to the agent that made that
part, with the finding as the only new instruction. A `spec` finding is the main agent's:
it corrects the spec (or the question set behind it) and then **restarts both arms**, because
each would otherwise fix against a different spec.

## Stopping

| Arm | Passes | Goes back | Stops early |
|---|---|---|---|
| A: Code | 3 | `error` findings, to the agent that made the part | The same message in two passes in a row |
| B: Diagram | 2 | `error` findings only | The same finding in two passes in a row |

`polish` findings from the review never go back: a reviewer always finds something, so
feeding them back means the loop never ends. They go into the hand-over.

When an arm stops without green, hand over its open findings as they are. A message that
returns unchanged after a fix means the cause is in the spec or the question set, not in the
code; say so.

**A later pass re-runs only what the change can reach.** The test agent is told which files
the fix touched and runs the checks that cover them, not the whole suite again: in Terraform
`terraform test -filter=tests/<file>.tftest.hcl` (repeatable), with the test file that
belongs to the changed resource plus the wiring and naming tests, which read across
resources. A change to a shared file (`providers.tf`, `variables.tf`, `locals.tf`, `data.tf`,
`naming.tf`, a stage file) can reach every test and gets the full run. The cheap checks
(`fmt`, `validate`, `check_render_coverage.py`, `check_pipeline.py`) run every time. **One full
run closes the arm**, once its filtered passes are green: a fix can break a neighbour that its
own test never touches, and a hand-over that was only ever tested in slices has not been
tested. A test that never ran, because an earlier block failed and skipped it, is not covered
by a filtered pass of another file.

**Never weaken a test to turn the arm green.** No removed `# decision:` assert, no
`# not-testable:` added to silence a failing check, no loosened expectation. A test that is
wrong is a finding of its own, reported with the reason.

## Brief every agent the same way

Each agent starts without this conversation. Its prompt carries:

1. **The role**, one sentence, and its place in the graph.
2. **Absolute paths**: the spec, the render root, the repository (read only).
3. **What to read first**: the skill file for its job, by path, then its references.
4. **The write boundary**: where it may write, and that it changes nothing else, does not
   commit and does not run `apply`.
5. **What not to read**: an existing render of the same spec. Copying it passes the checks
   and measures nothing.
6. **The report**: what it produced, what it could not do or had to assume, the layout the
   next agent depends on (code agent), the findings list (test and review agent).

Run the agents in the background and carry on with the other arm; the main agent never
repeats an agent's work while it runs. The brief of a later pass names the files the fix
changed, so the test agent can filter.

## The hand-over

The main agent's closing message is the explained plan, unchanged from the order of work:
code, tests, diagram, pipeline, open items and which changes are service-affecting. Add the
open findings of an arm that stopped without green, the `polish` findings of the review, and
which agents ran in how many passes.
