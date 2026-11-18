#!/usr/bin/env python3
"""Prints a pattern's share of an infra-spec.yaml, for the answers given.

Read-only. A pattern's pre-answers and wiring depend on its asks, and a run that works the
conditions out by hand drops a role or keeps the line of a part that does not exist. This
script resolves them: for one set of answers it prints, as YAML,

  pattern:     the pattern's id and every ask's answer (asked, or its default)
  deployment:  what the pattern answers in the deployment set, where it does
  resources:   every part that exists, with its purpose in the customer's language and the
               pattern's pre-answers under their question-set groups
  wiring:      the access lines, role assignments and secret references between the parts

Every value carries `source: pattern`. Nothing else is printed: what the pattern does not
answer - the customer's questions, the requirements, the deployment decisions, each set's
defaults - is resolved by the interview as for any system, and joins these blocks in the
spec the run writes.

Needs PyYAML (pip install pyyaml). Without it the script says so and exits 2.

Usage:
    python3 apply_pattern.py <pattern> [--answer <ask>=<value> ...] [--language de]
                             [--environments development,test,production] [--selected asked]

A pattern is an id under patterns/, a directory or a pattern.yaml. An ask without
`--answer` takes its default. `--environments` are the stages of the system: a per-stage
question's value is written once per stage. `--selected` is how the pattern was chosen:
`stated` (the request described it, the default) or `asked` (the person picked it).
Exit 0 printed, 2 could not apply (no pattern, an ask or a value the pattern does not have).
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pattern_lib as lib  # noqa: E402 - the one reader of a pattern
import check_spec  # noqa: E402 - the question index of the plugin's sets


def parse_answers(pairs, pattern, yaml):
    """`--answer id=value` pairs as {id: value}, each checked against its ask; or an error."""
    asks = {a['id']: a for a in (pattern.get('asks') or []) if isinstance(a, dict) and a.get('id')}
    answers = {}
    for pair in pairs:
        if '=' not in pair:
            return None, f"--answer {pair}: write <ask>=<value>"
        aid, raw = pair.split('=', 1)
        if aid not in asks:
            return None, f"--answer {aid}: the pattern asks {', '.join(asks) or 'nothing'}"
        value = yaml.safe_load(raw)
        ask = asks[aid]
        accepts = ask.get('accepts') if isinstance(ask.get('accepts'), list) else None
        if ask.get('type') == 'bool' and not isinstance(value, bool):
            return None, f"--answer {aid}={raw}: true or false"
        if ask.get('type') == 'enum' and accepts is not None and value not in accepts:
            return None, f"--answer {aid}={raw}: one of {', '.join(map(str, accepts))}"
        answers[aid] = value
    return answers, None


def main():
    ap = argparse.ArgumentParser(description="Print a pattern's share of an infra-spec.yaml.")
    ap.add_argument('pattern', help='a pattern id, directory or pattern.yaml')
    ap.add_argument('--answer', action='append', default=[], metavar='ASK=VALUE', help="an ask's answer; repeatable")
    ap.add_argument('--language', default='en', help="the customer's language for purposes and labels: en (default) or de")
    ap.add_argument('--environments', default='', help='the stages, comma-separated; a per-stage value is written per stage')
    ap.add_argument('--selected', default='stated', choices=['stated', 'asked'], help='how the pattern was chosen')
    args = ap.parse_args()

    try:
        import yaml
    except ImportError:
        print('[fail] no YAML parser available - pip install pyyaml', file=sys.stderr)
        return 2
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    pattern = lib.load(yaml, args.pattern)
    if not isinstance(pattern, dict):
        print(f"[fail] no pattern at {args.pattern} - the plugin has {', '.join(lib.pattern_ids()) or 'none'}", file=sys.stderr)
        return 2
    answers, problem = parse_answers(args.answer, pattern, yaml)
    if problem:
        print(f"[fail] {problem}", file=sys.stderr)
        return 2

    questions = check_spec.load_question_index(yaml)
    environments = [e.strip() for e in args.environments.split(',') if e.strip()]
    spec, _ = lib.apply(pattern, questions, answers, args.language, environments, args.selected)

    print(f"# The share of pattern {pattern.get('id')} - apply_pattern.py. Every value is source: pattern;")
    print('# the rest of the spec is the interview\'s.')
    print(yaml.safe_dump(spec, sort_keys=False, allow_unicode=True, default_flow_style=False, width=120), end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
