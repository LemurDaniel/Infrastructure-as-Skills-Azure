# Question-set generator

**Status:** sketch

## Idea

Given a resource type, the agent drafts a `questions.yaml` from the AVM module README
(inputs), the Azure docs and the guardrails: one question per real decision, a default with
its reasoning, the attribute it renders to, who resolves it. It validates the draft with
`check_question_set.py`.

## Output

A pull request with the draft question set, `notes.md` and both rendering references. A
human reviews every default and its reason - the generator proposes, it does not decide.

## Open questions

- Where the defaults come from when no guardrail covers them: flagged as assumed, never silent.
- How the draft is scored against the existing, hand-written families.
