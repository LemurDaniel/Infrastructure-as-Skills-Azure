#!/usr/bin/env python3
"""Tests for the patterns: the format check, the applier, and what a pattern gives a spec.

Three parts, each failing the run on its own:

  1. The checker. tests/fixtures/patterns/helpdesk is a valid pattern with one of everything
     the format has; it must pass check_pattern.py. Then each mutation breaks one rule in a
     copy - a part without a question set, an answer for a question the customer is asked,
     a role for a part without an identity, a secret no vault holds, a wiring line that
     outlives its part - and the check must fail with the message that names it. A mutation
     whose text is no longer in the fixture fails the run: a test that cannot break
     anything proves nothing.
  2. The plugin's patterns, in every variant their asks can produce: the pattern passes
     check_pattern.py; apply_pattern's share, put under a minimal head, passes
     check_spec.py; every value in it is `source: pattern`; and new_diagram.py draws it
     with every part and every access line between two parts.
  3. The spec check's pattern rules, on an applied spec: a value recorded `source: pattern`
     that the pattern does not give, an unknown pattern or ask, a role that is no built-in
     role, a secret the vault does not hold, an access line into nothing - each must fail.

Usage:
    python3 run_pattern_tests.py [-k <text>]     # cases whose name contains <text>

Needs PyYAML. Exit 0 all pass, 1 a test failed, 2 could not run.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, '..', 'scripts')
CHECK_PATTERN = os.path.join(SCRIPTS, 'check_pattern.py')
CHECK_SPEC = os.path.join(SCRIPTS, 'check_spec.py')
APPLY = os.path.join(SCRIPTS, 'apply_pattern.py')
DIAGRAM = os.path.join(HERE, '..', '..', 'iac-diagram', 'scripts', 'new_diagram.py')
FIXTURES = os.path.join(HERE, 'fixtures', 'patterns')
sys.path.insert(0, SCRIPTS)

# (name, text in the fixture, replacement, text the check's output must contain)
PATTERN_MUTATIONS = [
    ('an id that is not the directory', "id: helpdesk\n", "id: servicedesk\n", "is not its directory's name"),
    ('a title in one language', '  en: "Help desk"\n  de: "Helpdesk"\n', '  en: "Help desk"\n', 'title needs one line in each of en, de'),
    ('no selects_when', 'selects_when:\n  - "a help desk / ein Helpdesk"\n', '', 'selects_when is missing'),
    ('an unknown top-level field', "boundaries:\n", "notes: none\nboundaries:\n", "unknown top-level field 'notes'"),
    ('a part without a question set', "  app-service__web:\n    purpose: { en: \"Ticket application\"", "  web-farm:\n    purpose: { en: \"Ticket application\"", "no question set 'web-farm'"),
    ('a purpose in one language', 'purpose: { en: "Background jobs", de: "Hintergrundjobs" }', 'purpose: { en: "Background jobs" }', 'parts.function-app__jobs: purpose needs one line'),
    ('an ask without a default', "    type: bool\n    default: false\n", "    type: bool\n    required: true\n", 'asks.history: an ask needs a default'),
    ('an ask nobody is asked', "    default: false\n    resolved_by: interview\n    topic: data\n", "    default: false\n", 'asks.history: an ask is put to the customer'),
    ('an ask the deployment set already has', '- id: history\n', '- id: outage_impact\n', "the deployment set already asks 'outage_impact'"),
    ('a condition on an ask that does not exist', 'when: { ask: history, equals: true }\n    purpose', 'when: { ask: archive, equals: true }\n    purpose', "when names ask 'archive'"),
    ('a condition on a value the ask cannot take', 'when: { ask: sign_in, equals: company_accounts }\n    purpose', 'when: { ask: sign_in, equals: everyone }\n    purpose', "which sign_in cannot take"),
    ('an answer for a question the set does not have', "      value: system_assigned\n", "      value: system_assigned\n    favourite_colour:\n      value: blue\n", "has no question 'favourite_colour'"),
    ('an answer for a question the customer is asked', "    host_storage_account:\n", "    runtime_stack:\n      value: node\n      why: The jobs are written in JavaScript, which is the team's language.\n    host_storage_account:\n", 'the customer is asked this'),
    ('an answer for a question a requirement derives', "  key-vault:\n    secret_placeholders:\n", "  storage-account__host:\n    replication:\n      value: LRS\n      why: The host storage holds nothing that cannot be rebuilt from a deployment.\n  key-vault:\n    secret_placeholders:\n", 'a pattern never overrides a requirement'),
    ('an answer for a decision of the deployment', "  key-vault:\n    secret_placeholders:\n", "  storage-account__host:\n    public_network_access:\n      value: enabled\n      why: The host storage is reached by the function app from outside the network.\n  key-vault:\n    secret_placeholders:\n", 'inherits deployment.network_exposure'),
    ('a value the question does not accept', "    managed_identity:\n      value: user_assigned\n", "    managed_identity:\n      value: federated\n", "is not in the question's accepts"),
    ('an answer without its why', "      why: The host keeps its keys and locks in a storage account of its own.\n", "      why: needed\n", 'why is missing or one phrase'),
    ('a reference to what is no part', "value: { resource: storage-account__host }", "value: { resource: storage-account__data }", "which is not a part of the pattern"),
    ('a reference to the wrong kind of part', "value: { resource: storage-account__host }", "value: { resource: key-vault }", 'but a storage_account is a resource of storage-account'),
    ('a reference outside the pattern', "value: { resource: storage-account__host }", "value: { existing: storage_account }", 'a pattern knows no resource outside itself'),
    ('an access line into nothing', "    - from: function-app__jobs\n      to: storage-account__host\n", "    - from: function-app__jobs\n      to: redis-cache\n", "'redis-cache' is neither a part that exists"),
    ('a label in one language', 'label: { en: "working storage", de: "Arbeitsspeicher" }', 'label: { en: "working storage" }', 'label needs one line in each'),
    ('a role that is no built-in role', 'role: Storage Blob Data Owner', 'role: Storage Blob Owner', 'not a built-in role'),
    ('a role for a part with a user-assigned identity', "{ from: user-assigned-identity__jobs, to: storage-account__host,", "{ from: function-app__jobs, to: storage-account__host,", 'acts with a user-assigned identity'),
    ('a role for a part without an identity', "{ from: user-assigned-identity__jobs, to: storage-account__host,", "{ from: storage-account__host, to: storage-account__host,", 'has no identity of its own'),
    ('a role no access line explains', "    - from: function-app__jobs\n      to: storage-account__host\n      label: { en: \"working storage\", de: \"Arbeitsspeicher\" }\n", '', "a role nobody's connection explains"),
    ('a data-plane role on another service', "      to: key-vault\n      role: Key Vault Secrets User\n", "      to: key-vault\n      role: Cosmos DB Built-in Data Reader\n", "a role of cosmos-db's own role model"),
    ('a wiring line that outlives its part', "      label: { en: \"ticket history\", de: \"Ticket-Verlauf\" }\n      when: { ask: history, equals: true }\n", "      label: { en: \"ticket history\", de: \"Ticket-Verlauf\" }\n", "'cosmos-db' is neither a part that exists"),
    ('a secret the vault does not hold', "      secret_name: entra-client-secret\n", "      secret_name: api-key\n", "secret 'api-key' is not in pre_answers.key-vault.secret_placeholders"),
    ('a secret nobody may read', "    - from: app-service__web\n      to: key-vault\n      role: Key Vault Secrets User\n      when: { ask: sign_in, equals: company_accounts }\n", '', 'holds a secret-reading role on key-vault'),
    ('an identity nothing acts with', "      value: [{ resource: user-assigned-identity__jobs }]\n", "      value: []\n", 'an identity nothing acts with'),
    ('a wiring section the format does not have', "  secrets:\n", "  firewall_rules:\n", 'wiring.firewall_rules: not one of'),
]

HEAD = """schema_version: 1
spec:
  id: pattern-test
  target: terraform
context:
  language: en
  environments: [development, production]
  workload: test
deployment:
  network_exposure: { value: public, source: asked }
  network_ownership: { value: none, source: default }
"""

# On the applied default variant of ai-chat-rag with sign_in=company_accounts, chat_history=true.
SPEC_MUTATIONS = [
    ('a pattern the plugin does not ship', 'value: ai-chat-rag', 'value: ai-chat', "pattern.id 'ai-chat' is not a pattern of this plugin"),
    ('an answer to an ask the pattern does not have', '    chat_history:\n', '    chat_memory:\n', 'pattern.answers.chat_memory is no ask'),
    ('an answer the ask does not accept', '      value: company_accounts\n', '      value: everyone\n', "pattern.answers.sign_in is 'everyone'"),
    ('a pattern value the pattern does not give', "        value: serverless\n", "        value: provisioned\n", 'differs from what pattern ai-chat-rag answers'),
    ('a role added under source pattern', "    - from: search-service\n      to: foundry\n      role: Cognitive Services OpenAI User\n", "    - from: search-service\n      to: foundry\n      role: Cognitive Services OpenAI User\n    - from: search-service\n      to: key-vault\n      role: Key Vault Secrets User\n", 'wiring.role_assignments has source pattern, but differs'),
    ('a role that is no built-in role', 'role: Search Index Data Reader', 'role: Search Index Reader', "'Search Index Reader' is not a built-in role"),
    ('a role onto what is no resource', "    - from: search-service\n      to: foundry\n      role: Cognitive Services OpenAI User\n", "    - from: search-service\n      to: foundry__eu\n      role: Cognitive Services OpenAI User\n", "'foundry__eu' is not a resource of this spec"),
    ('an access line into nothing', "    - from: search-service\n      to: storage-account\n", "    - from: search-service\n      to: storage-acount\n", "'storage-acount' is neither a resource of this spec"),
    ('a secret the vault does not hold', '      secret_name: entra-client-secret\n', '      secret_name: api-key\n', "secret 'api-key' is not in resources.key-vault.security.secret_placeholders"),
    ('a secret in a vault the spec does not have', '      vault: key-vault\n', '      vault: key-vault__shared\n', "'key-vault__shared' is not a key vault of this spec"),
]


def run(script, *args):
    env = dict(os.environ, NO_COLOR='1', PYTHONIOENCODING='utf-8')
    proc = subprocess.run([sys.executable, script, *args], capture_output=True, text=True, encoding='utf-8', env=env)
    return proc.returncode, (proc.stdout or '') + (proc.stderr or '')


def main():
    ap = argparse.ArgumentParser(description='Run the pattern tests.')
    ap.add_argument('-k', default='', help='only cases whose name contains this text')
    args = ap.parse_args()
    try:
        import yaml
    except ImportError:
        print('[fail] no YAML parser available - pip install pyyaml')
        return 2
    import check_spec
    import pattern_lib as lib

    failed, count = [], 0

    def case(name, passed, detail=''):
        nonlocal count
        if args.k and args.k not in name:
            return
        count += 1
        print(f"[{' ok ' if passed else 'FAIL'}] {name}")
        if not passed:
            failed.append(name)
            for line in detail.strip().splitlines()[-12:]:
                print(f"         {line}")

    # --- 1. the checker, on the fixture pattern ------------------------------------
    fixture = os.path.join(FIXTURES, 'helpdesk', 'pattern.yaml')
    code, out = run(CHECK_PATTERN, fixture)
    case('fixture pattern passes', code == 0, out)
    with open(fixture, encoding='utf-8') as f:
        text = f.read()
    for name, old, new, expect in PATTERN_MUTATIONS:
        if args.k and args.k not in name:
            continue
        if old not in text:
            case(name, False, f"the mutation's text is no longer in the fixture: {old!r}")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(FIXTURES, os.path.join(tmp, 'patterns'))
            target = os.path.join(tmp, 'patterns', 'helpdesk', 'pattern.yaml')
            with open(target, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text.replace(old, new))
            code, out = run(CHECK_PATTERN, target)
        case(name, code == 1 and expect in out, f"exit {code}, expected to read: {expect}\n{out}")
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(FIXTURES, os.path.join(tmp, 'patterns'))
        with open(os.path.join(tmp, 'patterns', 'routing.md'), 'w', encoding='utf-8') as f:
            f.write('# Patterns\n\nNo row.\n')
        code, out = run(CHECK_PATTERN, os.path.join(tmp, 'patterns', 'helpdesk'))
    case('a pattern no routing row leads to', code == 1 and 'has no row leading to helpdesk/pattern.yaml' in out, out)

    # --- 2. the plugin's patterns, every variant -----------------------------------
    questions = check_spec.load_question_index(yaml)
    ids = lib.pattern_ids()
    case('the plugin ships patterns', bool(ids), 'patterns/ holds no pattern.yaml')
    code, out = run(CHECK_PATTERN)
    case("the plugin's patterns pass the format check", code == 0, out)
    for pid in ids:
        pattern = lib.load(yaml, pid)
        for answers in lib.variants(pattern):
            name = f"{pid} [{', '.join(f'{k}={v}' for k, v in answers.items()) or 'no ask'}]"
            if args.k and args.k not in name:
                continue
            share, resolved = lib.apply(pattern, questions, answers, 'en', ['development', 'production'])
            problems = []

            def sources(node, path=''):
                if isinstance(node, dict) and 'value' in node:
                    if node.get('source') != 'pattern':
                        problems.append(f"{path} is source {node.get('source')}, not pattern")
                elif isinstance(node, dict):
                    for k, v in node.items():
                        sources(v, f"{path}.{k}")
            for section in ('deployment', 'resources', 'wiring'):
                sources(share.get(section), section)
            if set(share['resources']) != set(resolved['parts']):
                problems.append('the resources of the share are not the parts that exist')

            with tempfile.TemporaryDirectory() as tmp:
                spec = os.path.join(tmp, 'infra-spec.yaml')
                with open(spec, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(HEAD + yaml.safe_dump(share, sort_keys=False, allow_unicode=True))
                code, out = run(CHECK_SPEC, spec)
                if code != 0:
                    problems.append(f"check_spec.py exit {code}\n{out}")
                drawn = os.path.join(tmp, 'd.drawio')
                proc = subprocess.run([sys.executable, '-I', DIAGRAM, spec, '--language', 'en', '--out', drawn],
                                      capture_output=True, text=True, encoding='utf-8')
                if proc.returncode != 0 or not os.path.isfile(drawn):
                    problems.append(f"new_diagram.py exit {proc.returncode}\n{proc.stdout}{proc.stderr}")
                else:
                    if 'not drawn' in (proc.stdout or '') + (proc.stderr or ''):
                        problems.append(f"new_diagram.py left a line out\n{proc.stdout}{proc.stderr}")
                    cells = list(ET.parse(drawn).getroot().iter('mxCell'))
                    labels = ' '.join(c.get('value') or '' for c in cells)
                    for key, part in resolved['parts'].items():
                        if lib.wording(part.get('purpose'), 'en') not in labels:
                            problems.append(f"the picture does not show {key} ({lib.wording(part.get('purpose'), 'en')})")
                    lines = [a for a in resolved['wiring'].get('access', []) if a['from'] in resolved['parts'] and a['to'] in resolved['parts']]
                    edges = [c for c in cells if c.get('edge') == '1']
                    if len(edges) < len({(a['from'], a['to']) for a in lines}):
                        problems.append(f"the picture has {len(edges)} line(s) for {len(lines)} connection(s) between parts")
            case(name, not problems, '\n'.join(problems))

    # --- 2b. the applier's command line ---------------------------------------------
    if ids:
        code, out = run(APPLY, 'ai-chat-rag', '--answer', 'sign_in=company_accounts', '--language', 'de')
        case('apply_pattern prints the share in the customer\'s language',
             code == 0 and 'Chat-Anwendung' in out and 'entra-client-secret' in out and 'source: pattern' in out, out)
        code, out = run(APPLY, 'ai-chat-rag', '--answer', 'colour=blue')
        case('apply_pattern refuses an ask the pattern does not have', code == 2 and 'the pattern asks' in out, out)
        code, out = run(APPLY, 'ai-chat-rag', '--answer', 'sign_in=everyone')
        case('apply_pattern refuses a value the ask does not accept', code == 2 and 'one of application, company_accounts' in out, out)
        code, out = run(APPLY, 'no-such-pattern')
        case('apply_pattern refuses an unknown pattern', code == 2 and 'no pattern at' in out, out)

    # --- 3. the spec check's pattern rules -------------------------------------------
    if 'ai-chat-rag' in ids:
        pattern = lib.load(yaml, 'ai-chat-rag')
        share, _ = lib.apply(pattern, questions, {'sign_in': 'company_accounts', 'chat_history': True}, 'en', ['development', 'production'])
        text = HEAD + yaml.safe_dump(share, sort_keys=False, allow_unicode=True)
        for name, old, new, expect in [('the applied spec passes', '', '', None)] + SPEC_MUTATIONS:
            if args.k and args.k not in name:
                continue
            if old and old not in text:
                case(name, False, f"the mutation's text is no longer in the applied spec: {old!r}")
                continue
            with tempfile.TemporaryDirectory() as tmp:
                spec = os.path.join(tmp, 'infra-spec.yaml')
                with open(spec, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(text.replace(old, new, 1) if old else text)
                code, out = run(CHECK_SPEC, spec)
            case(name, (code == 0) if expect is None else (code == 1 and expect in out), f"exit {code}, expected to read: {expect}\n{out}")
        no_pattern = text.replace(text[text.index('pattern:\n'):text.index('resources:\n')], '')
        with tempfile.TemporaryDirectory() as tmp:
            spec = os.path.join(tmp, 'infra-spec.yaml')
            with open(spec, 'w', encoding='utf-8', newline='\n') as f:
                f.write(no_pattern)
            code, out = run(CHECK_SPEC, spec)
        case('source pattern without a pattern', code == 1 and 'but the spec names no pattern' in out, out)

    print('-' * 70)
    if failed:
        print(f"{len(failed)} of {count} failed")
        return 1
    print(f"{count}/{count} passed")
    return 0


if __name__ == '__main__':
    sys.exit(main())
