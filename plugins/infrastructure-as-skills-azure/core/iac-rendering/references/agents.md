# Rendering with agents

A render is four deliverables from one spec: the code with its tests, the pipeline, the
diagram, and the checks that tie them to the spec. They share one input and little else, so
they can run as agents. This file is the protocol; the order of work in
[SKILL.md](../SKILL.md) stays the contract each agent follows.

**When.** Ask when the Agent tool is available and the spec has several resource families:
one `AskUserQuestion` at the start of `iac-authoring` Phase 5, before the diagram is drawn,
with two options - **Subagents (recommended)** and **Same session** - and run both loops
the way the user picked. Say in the option text what it costs: agents
run in parallel and check each other, but each starts cold and uses its own tokens; the same
session is cheaper and sequential. A small spec (one resource, one family) is not asked: it
is faster done in sequence, because every agent reads the spec, the references and the
guardrails again. Without the Agent tool, do the same steps in the same order yourself.

## Two loops from one spec, one after the other

```
 Loop 1 · Diagram and sign-off (iac-authoring, Phase 5)
   infra-spec.yaml ─> diagram agent ─> review agent ─> errors? ──no──> customer: fits? ──yes──┐
                            ^                            │ yes              │ change          │
                            └──────── findings ──────────┘                  v                 │
                                                                    spec corrected, redrawn   │
 Loop 2 · Code (iac-rendering) - starts only after the yes  <─────────────────────────────────┘
   code agent ─> pipeline agent ─> test agent ─> green? ──yes──> hand-over
        ^                                          │ no
        └──────────────── findings ────────────────┘
```

**The loops run one after the other, never in parallel** (owner's call, 2026-10-24,
replacing two parallel arms): the customer signs off on the picture, and the code - the
long, expensive loop - is rendered only from a spec whose picture they have agreed to. Loop
1 is Phase 5 of `iac-authoring`; the diagram agent and the review agent iterate on the
picture until it carries no real error, then the main agent shows it to the customer with
the one question of Phase 5. "Etwas ändern" corrects the spec and redraws; "ja" starts
Loop 2. In the same session, Loop 1 is the same loop with the session in both roles:
draw, then review the PNG against the checklist as a reader who has not seen the spec,
fix every `error`, and only then show it. In Loop 2 the agents never read each other's
output, and none of them touches the picture: the code is rendered from the spec the customer saw drawn, so the diagram stays as
signed off. The main agent starts the loops, counts the passes, routes findings and writes
the hand-over.

| Agent | Does | May write | Never |
|---|---|---|---|
| **Code** | Steps 1-7 of the order of work: AVM resolution, names, code, tests per decision | The render root only | Pipeline, diagram, `apply`, a commit |
| **Pipeline** | Step 10, after the code agent has reported the layout (root, stage files, backend keys, working directory) | The pipeline files only | Code, tests |
| **Test** | `fmt`, `validate`, `test`, `check_render_coverage.py`, `check_pipeline.py` | Nothing | Fixing what it finds |
| **Diagram** | Loop 1 only: `iac-diagram` from the spec, then the review's findings fixed by hand in the `.drawio` | `infra-diagram.drawio.png` beside the spec | Code, pipeline, `new_diagram.py` |
| **Review** | Loop 1: reads the PNG and compares it with the spec | Nothing | Fixing what it finds |

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
it corrects the spec (or the question set behind it) and goes back to Loop 1: the picture
is redrawn, and when the correction changed it, the customer sees it again before Loop 2
is restarted on the corrected spec. Loop 2 never redraws on its own.

## Stopping

| Loop | Passes | Goes back | Stops early |
|---|---|---|---|
| 1: Diagram | 2 | `error` findings only | The same finding in two passes in a row *after a re-slot of the shapes* (checklist in `iac-diagram/SKILL.md`); the customer then sees the picture with the error named as open |
| 2: Code | 3 | `error` findings, to the agent that made the part | The same message in two passes in a row |

`polish` findings from the review never go back: a reviewer always finds something, so
feeding them back means the loop never ends. They go into the hand-over. For the same
reason the review is capped: **at most 8 findings per pass, errors first, at most 3
`polish`**, one finding per fault even when it hits several cells, the PNG and the spec
as its sources and the `.drawio` only for a coordinate, no pixel sampling; a second pass
re-checks the first pass's findings and what the fix touched, never the whole picture
again. The first dry run's review (2026-10-24) returned 17 findings after six minutes;
the ceiling exists because of it.

When a loop stops without green, hand over its open findings as they are. A message that
returns unchanged after a fix means the cause is in the spec or the question set, not in the
code; say so.

**A later pass re-runs only what the change can reach.** The test agent is told which files
the fix touched and runs the checks that cover them, not the whole suite again: in Terraform
`terraform test -filter=tests/<file>.tftest.hcl` (repeatable), with the test file that
belongs to the changed resource plus the wiring and naming tests, which read across
resources. A change to a shared file (`providers.tf`, `variables.tf`, `locals.tf`, `data.tf`,
`naming.tf`, a stage file) can reach every test and gets the full run. The cheap checks
(`fmt`, `validate`, `check_render_coverage.py`, `check_pipeline.py`) run every time. **One full
run closes the loop**, once its filtered passes are green: a fix can break a neighbour that its
own test never touches, and a hand-over that was only ever tested in slices has not been
tested. A test that never ran, because an earlier block failed and skipped it, is not covered
by a filtered pass of another file.

**Never weaken a test to turn the loop green.** No removed `# decision:` assert, no
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

Loop 1's two briefs carry, in addition:

- **Review agent**: the PNG and the spec as its sources, the `.drawio` only for a
  coordinate; the checklist (`iac-diagram/SKILL.md#the-review-checklist`, worked through in
  order, every edge traced end to end - never "looked at once"); the ceiling (8 findings, errors
  first, at most 3 polish, one finding per fault, cell ids on every finding, no pixel
  sampling); on a second pass, the first pass's list and the cells the fix touched, and
  nothing else to look at.
- **Diagram agent**: the review's `error` findings verbatim, with their cell ids; the path
  of the draft to work on (regenerated by the main agent after any `spec` finding); the
  write boundary - the `.drawio` and the `.drawio.png` beside the spec, never
  `new_diagram.py`, never the repository; the export chain to run after every round:
  `verify_diagram.py`, `export_diagram.py` (or the substitute `iac-diagram/SKILL.md`
  allows where draw.io is missing), `drawio_png.py check`, then look at the PNG itself;
  the `polish` findings it is told not to fix, so it can say which are script faults for
  the hand-over.

Run the agents in the background; the main agent never repeats an agent's work while it
runs, and never starts Loop 2 before the customer's yes. The brief of a later pass names the files the fix
changed, so the test agent can filter.

## The hand-over

The main agent's closing message is the explained plan, unchanged from the order of work:
code, tests, the signed-off diagram, pipeline, open items and which changes are service-affecting. Add the
open findings of a loop that stopped without green, the `polish` findings of the review, and
which agents ran in how many passes.
