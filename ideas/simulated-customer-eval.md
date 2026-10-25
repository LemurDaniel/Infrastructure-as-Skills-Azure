# Simulated customer in the evals

**Status:** sketch

## Idea

The eval runs are headless: nobody answers `AskUserQuestion`, so the spec is written from
the prompt alone and the interview itself - the customer batches of Phase 3, the design
tick list of Phase 4, the sign-off before code - never runs. The graders see the result,
not the path. A simulated customer answers the questions from a script, so the
interview path is exercised and graded.

## Sketch

- A case carries an `answers.yaml`: question id -> answer, plus a fallback ("the default").
- The harness has no custom-code graders and no user-input hook, so the answers need either
  a stub for `AskUserQuestion` in the eval config, or the [eval agent](eval-agent.md)
  driving the session (an SDK client that answers by script).
- Graders then cover what headless runs cannot: every `resolved_by: interview` question
  reached the person, none of the parameterized context was asked, the `requirements` group
  came in full, Phase 4 shows the tick list before any file, no code before the yes.

## Open questions

- Does `claude plugin eval` offer any way to answer tool prompts? If not, this lives in the
  eval agent, not in the suite.
- Scripted answers make the run deterministic where a real customer is not; a second
  persona that answers vaguely would test the open-item paths.
